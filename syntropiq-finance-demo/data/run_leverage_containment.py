#!/usr/bin/env python3
"""
Systemic Correlation + Leverage Spiral Containment Demo

Wrapper-only demo using real market data and unchanged Syntropiq governance kernel.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# allow imports when run from syntropiq-finance-demo/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")
DB_PATH = os.path.join(DATA_DIR, "finance_leverage_demo.db")

STARTING_CAPITAL = 10_000_000.0
INITIAL_TRUST = 0.75
INITIAL_TRUST_THRESHOLD = 0.70
INITIAL_SUPPRESSION_THRESHOLD = 0.75
INITIAL_DRIFT_DELTA = 0.10

ROUTING_MODE = "deterministic"
WINDOW = 8
EPS = 1e-9

AGENTS = {
    "high_beta_momentum": {"label": "High Beta Momentum"},
    "short_volatility": {"label": "Short Volatility"},
    "leverage_trend": {"label": "Leverage Trend"},
    "credit_carry": {"label": "Credit Carry"},
    "defensive_bonds": {"label": "Defensive Bonds"},
}
RISKY_AGENTS = [
    "high_beta_momentum",
    "short_volatility",
    "leverage_trend",
    "credit_carry",
]


@dataclass
class WeekContext:
    week: int
    date: str
    regime: str
    benchmark_return: float
    spy_vol_4w: float
    volatility_p75: float
    correlation_metric: float
    leverage_exposure: Dict[str, float]
    agent_returns: Dict[str, float]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mean_last(values: List[float], n: int) -> float:
    if not values:
        return 0.0
    w = values[-n:]
    return sum(w) / len(w)


def stdev_last(values: List[float], n: int) -> float:
    w = values[-n:]
    if len(w) <= 1:
        return 0.0
    return statistics.pstdev(w)


def max_drawdown_from_returns(returns: List[float]) -> float:
    if not returns:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= 1.0 + r
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def pearson_corr(x: List[float], y: List[float]) -> float:
    if len(x) != len(y) or len(x) < 3:
        return 0.0
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx <= 0 or vy <= 0:
        return 0.0
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(len(x)))
    return cov / ((vx ** 0.5) * (vy ** 0.5))


def rolling_metrics(delta_hist: List[float], agent_hist: List[float], bench_hist: List[float]) -> Dict[str, float]:
    d = delta_hist[-WINDOW:]
    a = agent_hist[-WINDOW:]
    b = bench_hist[-WINDOW:]

    if not d:
        return {
            "count": 0,
            "alpha_8w": 0.0,
            "min_delta_8w": 0.0,
            "dd_agent_8w": 0.0,
            "dd_bench_8w": 0.0,
            "dd_ratio": 0.0,
        }

    dd_agent_8w = max_drawdown_from_returns(a)
    dd_bench_8w = max_drawdown_from_returns(b)
    return {
        "count": len(d),
        "alpha_8w": sum(d) / len(d),
        "min_delta_8w": min(d),
        "dd_agent_8w": dd_agent_8w,
        "dd_bench_8w": dd_bench_8w,
        "dd_ratio": dd_agent_8w / max(dd_bench_8w, EPS),
    }


def calm_streak(spy_hist: List[float]) -> int:
    streak = 0
    for r in reversed(spy_hist):
        if abs(r) < 0.008:
            streak += 1
        else:
            break
    return streak


def compute_agent_returns(
    week_idx: int,
    week_data: dict,
    market_hist: Dict[str, List[float]],
    vol_p75: float,
    regime_shift_week: int,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, dict], float]:
    tick = week_data["tickers"]

    spy_r = float(tick["SPY"]["weekly_return"])
    qqq_r = float(tick["QQQ"]["weekly_return"])
    iwm_r = float(tick["IWM"]["weekly_return"])
    hyg_r = float(tick["HYG"]["weekly_return"])
    xlf_r = float(tick["XLF"]["weekly_return"])
    agg_r = float(tick["AGG"]["weekly_return"])
    tlt_r = float(tick["TLT"]["weekly_return"])
    gld_r = float(tick["GLD"]["weekly_return"])

    spy_hist = market_hist["SPY"][:week_idx]
    qqq_hist = market_hist["QQQ"][:week_idx]
    hyg_hist = market_hist["HYG"][:week_idx]
    agg_hist = market_hist["AGG"][:week_idx]

    spy_vol_4w = stdev_last(spy_hist, 4)
    stress = (week_data.get("regime") == "stress") or (spy_vol_4w > vol_p75)

    # deterministic liquidity shock: when stress, risky agents share a common downside factor
    shock = 0.0
    if stress:
        shock = -0.45 * abs(min(spy_r, 0.0)) - 0.20 * abs(qqq_r)

    ret: Dict[str, float] = {}
    lev: Dict[str, float] = {}
    drift_flags: Dict[str, dict] = {}

    # 1) high_beta_momentum
    trend_8 = 0.5 * mean_last(spy_hist, 8) + 0.5 * mean_last(qqq_hist, 8)
    hb_base = 0.7 * qqq_r + 0.3 * iwm_r if trend_8 >= 0 else 0.55 * qqq_r + 0.45 * iwm_r
    hb_lev = clamp(0.9, 4.2, 0.022 / max(spy_vol_4w, 1e-6))
    hb_drift = False
    if (week_idx + 1) >= regime_shift_week and stress:
        hb_drift = True
        hb_lev = max(hb_lev, 3.4)  # fails to de-risk during spike
    ret["high_beta_momentum"] = hb_lev * hb_base + 0.85 * shock
    lev["high_beta_momentum"] = hb_lev
    drift_flags["high_beta_momentum"] = {
        "active": hb_drift,
        "reason": "vol_spike_deleverage_failure" if hb_drift else "",
    }

    # 2) short_volatility
    streak = calm_streak(spy_hist)
    sv_size = clamp(0.8, 3.8, 1.0 + 0.32 * max(0, streak - 1))
    sv_drift = streak >= 4
    carry_gain = 0.0035 * sv_size
    convexity_loss = sv_size * max(0.0, spy_vol_4w - vol_p75) * 6.0
    downside_loss = sv_size * max(0.0, -spy_r) * 1.2
    sv_ret = carry_gain + 0.08 * spy_r - convexity_loss - downside_loss
    if stress:
        sv_ret += 1.00 * shock
    ret["short_volatility"] = sv_ret
    lev["short_volatility"] = sv_size
    drift_flags["short_volatility"] = {
        "active": sv_drift,
        "reason": "size_increase_after_calm" if sv_drift else "",
    }

    # 3) leverage_trend
    lt_trend = mean_last(spy_hist, 12)
    lt_base = spy_r if lt_trend >= -0.003 else (0.6 * agg_r + 0.4 * tlt_r)
    lt_lev = clamp(1.0, 4.0, 0.020 / max(spy_vol_4w, 1e-6))
    lt_drift = False
    if (week_idx + 1) >= regime_shift_week and stress:
        lt_drift = True
        lt_base = spy_r
        lt_lev = max(lt_lev, 3.2)
    ret["leverage_trend"] = lt_lev * lt_base + 0.80 * shock
    lev["leverage_trend"] = lt_lev
    drift_flags["leverage_trend"] = {
        "active": lt_drift,
        "reason": "trend_lag_leverage_stickiness" if lt_drift else "",
    }

    # 4) credit_carry
    spread_signal = mean_last(hyg_hist, 6) - mean_last(agg_hist, 6)
    cc_base = 0.82 * hyg_r + 0.18 * xlf_r if spread_signal > -0.001 else 0.65 * agg_r + 0.35 * tlt_r
    cc_lev = clamp(0.8, 2.6, 0.017 / max(spy_vol_4w, 1e-6))
    cc_drift = stress
    cc_ret = cc_lev * cc_base + (0.45 * shock if stress else 0.0)
    ret["credit_carry"] = cc_ret
    lev["credit_carry"] = cc_lev
    drift_flags["credit_carry"] = {
        "active": cc_drift,
        "reason": "liquidity_spread_widening" if cc_drift else "",
    }

    # 5) defensive_bonds
    db_lev = clamp(0.8, 1.25, 0.012 / max(spy_vol_4w, 1e-6))
    db_ret = db_lev * (0.55 * agg_r + 0.35 * tlt_r + 0.10 * gld_r)
    if stress:
        db_ret += 0.12 * abs(min(spy_r, 0.0))
    ret["defensive_bonds"] = db_ret
    lev["defensive_bonds"] = db_lev
    drift_flags["defensive_bonds"] = {"active": False, "reason": ""}

    return ret, lev, drift_flags, spy_vol_4w


def correlation_metric_from_history(agent_return_hist: Dict[str, List[float]]) -> float:
    pairs: List[float] = []
    for i, a in enumerate(RISKY_AGENTS):
        for b in RISKY_AGENTS[i + 1 :]:
            xa = agent_return_hist.get(a, [])[-WINDOW:]
            xb = agent_return_hist.get(b, [])[-WINDOW:]
            c = pearson_corr(xa, xb)
            pairs.append(max(0.0, c))
    if not pairs:
        return 0.0
    return sum(pairs) / len(pairs)


class SystemicRiskExecutor:
    def __init__(self):
        self.ctx_by_week: Dict[int, WeekContext] = {}
        self.delta_hist: Dict[str, List[float]] = {}
        self.agent_hist: Dict[str, List[float]] = {}
        self.bench_hist: Dict[str, List[float]] = {}
        self.last_seen_week: Dict[str, int] = {}

    def set_week_context(self, ctx: WeekContext) -> None:
        self.ctx_by_week[ctx.week] = ctx

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        week = int(task.metadata["week"])
        ctx = self.ctx_by_week[week]

        a_ret = ctx.agent_returns[agent.id]
        b_ret = ctx.benchmark_return
        delta = a_ret - b_ret

        if self.last_seen_week.get(agent.id) != week:
            self.delta_hist.setdefault(agent.id, []).append(delta)
            self.agent_hist.setdefault(agent.id, []).append(a_ret)
            self.bench_hist.setdefault(agent.id, []).append(b_ret)
            self.last_seen_week[agent.id] = week

        m = rolling_metrics(
            self.delta_hist.get(agent.id, []),
            self.agent_hist.get(agent.id, []),
            self.bench_hist.get(agent.id, []),
        )

        if m["count"] < WINDOW:
            success = True
            outcome = "warmup"
        else:
            lev = ctx.leverage_exposure.get(agent.id, 1.0)
            fail_leverage = lev > 2.8 and ctx.spy_vol_4w > ctx.volatility_p75
            fail_corr = agent.id in RISKY_AGENTS and ctx.correlation_metric > 0.8
            structural_failure = (
                m["dd_ratio"] >= 1.6
                or m["alpha_8w"] <= -0.02
                or fail_leverage
                or fail_corr
            )
            success = not structural_failure
            outcome = "failure" if structural_failure else "success"

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.001,
            metadata={
                "week": week,
                "date": ctx.date,
                "regime": ctx.regime,
                "weekly_return": round(a_ret, 6),
                "benchmark_return": round(b_ret, 6),
                "delta": round(delta, 6),
                "alpha_8w": round(m["alpha_8w"], 6),
                "dd_ratio": round(m["dd_ratio"], 6),
                "spy_vol_4w": round(ctx.spy_vol_4w, 6),
                "volatility_p75": round(ctx.volatility_p75, 6),
                "correlation_metric": round(ctx.correlation_metric, 6),
                "leverage_exposure": round(ctx.leverage_exposure.get(agent.id, 1.0), 4),
                "signal_class": outcome,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in AGENTS


def build_tasks_for_week(week_data: dict, week: int, agent_returns: Dict[str, float], leverages: Dict[str, float]) -> List[Task]:
    tasks: List[Task] = []
    regime = week_data.get("regime", "bull")
    urgency = 0.82 if regime == "stress" else 0.62
    bm_ret = float(week_data["benchmark_return"])

    for aid in AGENTS:
        delta = agent_returns[aid] - bm_ret
        lev = leverages[aid]
        impact = clamp(0.28 + 16.0 * abs(delta) + 0.08 * lev, 0.10, 1.00)
        risk = clamp(0.08 + 12.0 * max(0.0, -delta) + 0.06 * lev, 0.05, 0.50)
        tasks.append(
            Task(
                id=f"SYSTEMIC_{week:03d}_{aid}",
                impact=round(impact, 4),
                urgency=urgency,
                risk=round(risk, 4),
                metadata={
                    "week": week,
                    "date": week_data["date"],
                    "regime": regime,
                    "agent": aid,
                    "delta": round(delta, 6),
                    "leverage": round(lev, 4),
                },
            )
        )

    return tasks


def status_from_kernel(loop: GovernanceLoop, aid: str) -> str:
    if aid in loop.trust_engine.suppressed_agents:
        return "suppressed"
    if aid in loop.trust_engine.probation_agents:
        return "probation"
    return "active"


def governed_weights(
    agents: Dict[str, Agent],
    status_map: Dict[str, str],
    correlation: float,
    spy_vol_4w: float,
    vol_p75: float,
) -> Dict[str, float]:
    raw = {
        aid: (0.0 if status_map[aid] == "suppressed" else max(agents[aid].trust_score, 0.0))
        for aid in AGENTS
    }
    total = sum(raw.values())
    if total <= 0:
        return {aid: 0.0 for aid in AGENTS}
    w = {aid: raw[aid] / total for aid in AGENTS}

    # Dynamic authority cap under systemic risk: avoid concentration in risky sleeves.
    cap = 0.50
    if correlation > 0.8 or spy_vol_4w > vol_p75:
        cap = 0.35

    excess = 0.0
    for aid in RISKY_AGENTS:
        if w[aid] > cap:
            excess += w[aid] - cap
            w[aid] = cap

    if status_map["defensive_bonds"] != "suppressed":
        w["defensive_bonds"] += excess
    else:
        active_others = [aid for aid in AGENTS if aid != "defensive_bonds" and status_map[aid] != "suppressed"]
        s = sum(w[aid] for aid in active_others)
        if s > 0:
            for aid in active_others:
                w[aid] += excess * (w[aid] / s)

    total2 = sum(w.values())
    if total2 <= 0:
        return {aid: 0.0 for aid in AGENTS}
    return {aid: w[aid] / total2 for aid in AGENTS}


def run_leverage_containment() -> dict:
    if not os.path.exists(MARKET_DATA_PATH):
        raise RuntimeError("market_data.json missing. Run: python3 data/fetch_market_data.py")

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks = market_data.get("weeks", [])
    if not weeks:
        raise RuntimeError("No weekly market rows found")

    regime_shift_week = int(market_data.get("regime_shift_week") or 53)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    state = PersistentStateManager(db_path=DB_PATH)

    try:
        registry = AgentRegistry(state)
        for aid in AGENTS:
            registry.register_agent(
                agent_id=aid,
                capabilities=["allocation", "risk_management"],
                initial_trust_score=INITIAL_TRUST,
                status="active",
            )

        loop = GovernanceLoop(
            state_manager=state,
            trust_threshold=INITIAL_TRUST_THRESHOLD,
            suppression_threshold=INITIAL_SUPPRESSION_THRESHOLD,
            drift_delta=INITIAL_DRIFT_DELTA,
            routing_mode=ROUTING_MODE,
        )
        loop.trust_engine.MAX_REDEMPTION_CYCLES = 200

        executor = SystemicRiskExecutor()

        market_hist: Dict[str, List[float]] = {t: [] for t in weeks[0]["tickers"].keys()}
        for w in weeks:
            for t in market_hist:
                market_hist[t].append(float(w["tickers"][t]["weekly_return"]))

        spy_series = market_hist["SPY"]
        vol_series = [stdev_last(spy_series[:i], 4) for i in range(1, len(spy_series) + 1)]
        vol_sorted = sorted(vol_series)
        vol_p75 = vol_sorted[int(0.75 * (len(vol_sorted) - 1))] if vol_sorted else 0.02

        governed_value = STARTING_CAPITAL
        ungoverned_value = STARTING_CAPITAL
        benchmark_value = STARTING_CAPITAL

        peak_gov = governed_value
        peak_ung = ungoverned_value
        peak_bm = benchmark_value
        max_dd_gov = 0.0
        max_dd_ung = 0.0
        max_dd_bm = 0.0

        peak_leverage_exposure = 0.0
        peak_correlation = 0.0
        weeks_high_correlation = 0
        suppression_events = 0

        timeline: List[dict] = []
        previous_status = {aid: "active" for aid in AGENTS}
        previous_mutation = {
            "trust_threshold": INITIAL_TRUST_THRESHOLD,
            "suppression_threshold": INITIAL_SUPPRESSION_THRESHOLD,
            "drift_delta": INITIAL_DRIFT_DELTA,
        }

        cumulative_returns = {aid: 0.0 for aid in AGENTS}
        agent_return_hist = {aid: [] for aid in AGENTS}

        print("\n" + "=" * 84)
        print("  SYSTEMIC CORRELATION + LEVERAGE SPIRAL CONTAINMENT")
        print("=" * 84)

        for idx, w in enumerate(weeks):
            week = int(w["week"])
            date = w["date"]
            regime = w.get("regime", "bull")
            bm_ret = float(w["benchmark_return"])

            returns, leverages, drift_flags, spy_vol_4w = compute_agent_returns(
                idx, w, market_hist, vol_p75, regime_shift_week
            )

            for aid in AGENTS:
                agent_return_hist[aid].append(returns[aid])
            corr = correlation_metric_from_history(agent_return_hist)
            peak_correlation = max(peak_correlation, corr)
            if corr > 0.8:
                weeks_high_correlation += 1

            ungov_weights = {aid: 1.0 / len(AGENTS) for aid in AGENTS}
            ungoverned_ret = sum(ungov_weights[aid] * returns[aid] for aid in AGENTS)
            ungov_leverage = sum(ungov_weights[aid] * leverages[aid] for aid in AGENTS)

            executor.set_week_context(
                WeekContext(
                    week=week,
                    date=date,
                    regime=regime,
                    benchmark_return=bm_ret,
                    spy_vol_4w=spy_vol_4w,
                    volatility_p75=vol_p75,
                    correlation_metric=corr,
                    leverage_exposure=leverages,
                    agent_returns=returns,
                )
            )

            tasks = build_tasks_for_week(w, week, returns, leverages)
            agents = registry.get_agents_dict()

            froze = False
            week_events: List[dict] = []

            try:
                result = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"SYSTEMIC_{week:03d}",
                )
            except ValueError as e:
                if "Total of weights must be greater than zero" not in str(e):
                    raise
                froze = True
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] ROUTING FREEZE — governed shifted to defensive sleeve",
                    }
                )
                result = {
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {"tasks_executed": 0, "successes": 0, "failures": 0, "avg_latency": 0.0},
                }
            except CircuitBreakerTriggered as e:
                froze = True
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] CIRCUIT BREAKER — {str(e)}",
                    }
                )
                result = {
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {"tasks_executed": 0, "successes": 0, "failures": 0, "avg_latency": 0.0},
                }

            registry.sync_trust_scores()
            agents = registry.get_agents_dict()
            status_map = {aid: status_from_kernel(loop, aid) for aid in AGENTS}

            for aid in AGENTS:
                if previous_status[aid] != status_map[aid] and status_map[aid] == "suppressed":
                    suppression_events += 1
                    week_events.append(
                        {
                            "type": "suppressed",
                            "color": "red",
                            "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} SUPPRESSED",
                        }
                    )

            if corr > 0.8:
                week_events.append(
                    {
                        "type": "systemic_correlation",
                        "color": "amber",
                        "text": f"[WEEK {week:02d}] SYSTEMIC CORRELATION SPIKE {corr:.2f}",
                    }
                )

            if froze:
                gov_weights = {aid: 0.0 for aid in AGENTS}
                gov_weights["defensive_bonds"] = 1.0
                governed_ret = returns["defensive_bonds"]
            else:
                gov_weights = governed_weights(agents, status_map, corr, spy_vol_4w, vol_p75)
                governed_ret = sum(gov_weights[aid] * returns[aid] for aid in AGENTS)
                previous_mutation = result.get("mutation", previous_mutation)

            gov_leverage = sum(gov_weights[aid] * leverages[aid] for aid in AGENTS)
            peak_leverage_exposure = max(peak_leverage_exposure, max(ungov_leverage, gov_leverage))

            governed_value *= 1.0 + governed_ret
            ungoverned_value *= 1.0 + ungoverned_ret
            benchmark_value *= 1.0 + bm_ret

            peak_gov = max(peak_gov, governed_value)
            peak_ung = max(peak_ung, ungoverned_value)
            peak_bm = max(peak_bm, benchmark_value)
            max_dd_gov = min(max_dd_gov, (governed_value - peak_gov) / peak_gov)
            max_dd_ung = min(max_dd_ung, (ungoverned_value - peak_ung) / peak_ung)
            max_dd_bm = min(max_dd_bm, (benchmark_value - peak_bm) / peak_bm)

            for aid in AGENTS:
                cumulative_returns[aid] += returns[aid]

            timeline.append(
                {
                    "week": week,
                    "date": date,
                    "regime": regime,
                    "agents": {
                        aid: {
                            "trust": round(agents[aid].trust_score, 4),
                            "authority_weight": round(gov_weights[aid], 4),
                            "status": status_map[aid],
                            "weekly_return": round(returns[aid], 6),
                            "benchmark_delta": round(returns[aid] - bm_ret, 6),
                            "cumulative_return": round(cumulative_returns[aid], 6),
                        }
                        for aid in AGENTS
                    },
                    "portfolio_value": round(governed_value, 0),
                    "benchmark_value": round(benchmark_value, 0),
                    "portfolio_return": round(governed_ret, 6),
                    "benchmark_return": round(bm_ret, 6),
                    "outperformance_dollar": round(governed_value - benchmark_value, 0),
                    "outperformance_pct": round((governed_value / benchmark_value - 1.0) * 100, 2),
                    "governed_portfolio_value": round(governed_value, 0),
                    "ungoverned_portfolio_value": round(ungoverned_value, 0),
                    "ungoverned_return": round(ungoverned_ret, 6),
                    "leverage_exposure": round(gov_leverage, 4),
                    "ungoverned_leverage_exposure": round(ungov_leverage, 4),
                    "correlation_metric": round(corr, 4),
                    "drift_flags": drift_flags,
                    "events": week_events,
                }
            )

            previous_status = status_map

            if week % 10 == 0 or week == 1:
                print(
                    f"  Week {week:3d} [{regime:6s}] GOV ${governed_value:>11,.0f} | "
                    f"UNG ${ungoverned_value:>11,.0f} | CORR {corr:.2f} | "
                    f"LEV gov/ung {gov_leverage:.2f}/{ungov_leverage:.2f}"
                )

        summary = {
            "final_governed_value": round(governed_value, 0),
            "final_ungoverned_value": round(ungoverned_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "max_drawdown_governed": round(max_dd_gov, 4),
            "max_drawdown_ungoverned": round(max_dd_ung, 4),
            "max_drawdown_benchmark": round(max_dd_bm, 4),
            "peak_leverage_exposure": round(peak_leverage_exposure, 4),
            "peak_correlation": round(peak_correlation, 4),
            "weeks_high_correlation": weeks_high_correlation,
            "suppression_events": suppression_events,
            "governance_events_count": sum(len(w["events"]) for w in timeline),
            # compatibility keys
            "final_portfolio_value": round(governed_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "total_outperformance_pct": round((governed_value / benchmark_value - 1.0) * 100, 2),
            "total_outperformance_pct_ungov_vs_bm": round((ungoverned_value / benchmark_value - 1.0) * 100, 2),
            "total_outperformance_pct_gov_vs_ungov": round((governed_value / ungoverned_value - 1.0) * 100, 2),
            "benchmark": "60% SPY / 40% AGG",
            "data_source": "yfinance (real)",
            "total_weeks": len(timeline),
            "sleeves": list(AGENTS.keys()),
        }

        out = {"summary": summary, "timeline": timeline}
        with open(OUTPUT_PATH, "w") as f:
            json.dump(out, f, indent=2)

        print("\n" + "=" * 84)
        print("  SYSTEMIC CONTAINMENT COMPLETE")
        print("=" * 84)
        print(f"  GOV value: ${governed_value:,.0f}")
        print(f"  UNG value: ${ungoverned_value:,.0f}")
        print(f"  BM  value: ${benchmark_value:,.0f}")
        print(f"  DD GOV/UNG/BM: {max_dd_gov:.2%}/{max_dd_ung:.2%}/{max_dd_bm:.2%}")
        print(f"  Peak leverage exposure: {peak_leverage_exposure:.2f}x")
        print(f"  Peak correlation: {peak_correlation:.2f} | weeks >0.8: {weeks_high_correlation}")
        print(f"  Suppression events: {suppression_events}")
        print(f"  Output: {OUTPUT_PATH}")

        return out

    finally:
        state.close()


if __name__ == "__main__":
    run_leverage_containment()
