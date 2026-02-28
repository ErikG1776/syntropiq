#!/usr/bin/env python3
"""
Crisis 1: Synchronized Deleveraging Cascade Containment

Wrapper-only finance simulation using real market data and unchanged Syntropiq kernel.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Dict, List

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
DB_PATH = os.path.join(DATA_DIR, "finance_cascade_demo.db")

STARTING_CAPITAL = 10_000_000.0
INITIAL_TRUST = 0.75
INITIAL_TRUST_THRESHOLD = 0.70
INITIAL_SUPPRESSION_THRESHOLD = 0.75
INITIAL_DRIFT_DELTA = 0.10

ROUTING_MODE = "deterministic"
WINDOW = 8
TARGET_VOL = 0.02
SPIRAL_K = 0.35
EPS = 1e-9

AGENTS = {
    "high_beta_momentum": {"label": "High Beta Momentum"},
    "leverage_trend": {"label": "Leverage Trend"},
    "short_vol": {"label": "Short Vol"},
    "credit_carry": {"label": "Credit Carry"},
    "defensive_bonds": {"label": "Defensive Bonds"},
}
RISKY_AGENTS = ["high_beta_momentum", "leverage_trend", "short_vol", "credit_carry"]


@dataclass
class WeekContext:
    week: int
    date: str
    regime: str
    benchmark_return: float
    realized_vol_4w: float
    p75_vol_4w: float
    systemic_corr: float
    agent_returns: Dict[str, float]
    agent_leverage: Dict[str, float]


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
    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        eq *= 1.0 + r
        peak = max(peak, eq)
        dd = (peak - eq) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def rolling_metrics(deltas: List[float], agent_returns: List[float], bench_returns: List[float]) -> Dict[str, float]:
    d = deltas[-WINDOW:]
    a = agent_returns[-WINDOW:]
    b = bench_returns[-WINDOW:]
    if not d:
        return {
            "count": 0,
            "min_delta_8w": 0.0,
            "dd_agent_8w": 0.0,
            "dd_bench_8w": 0.0,
            "dd_ratio_8w": 0.0,
        }
    dd_agent = max_drawdown_from_returns(a)
    dd_bench = max_drawdown_from_returns(b)
    return {
        "count": len(d),
        "min_delta_8w": min(d),
        "dd_agent_8w": dd_agent,
        "dd_bench_8w": dd_bench,
        "dd_ratio_8w": dd_agent / max(dd_bench, EPS),
    }


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


def systemic_corr_from_hist(agent_hist: Dict[str, List[float]]) -> float:
    vals: List[float] = []
    for i, a in enumerate(RISKY_AGENTS):
        for b in RISKY_AGENTS[i + 1 :]:
            vals.append(pearson_corr(agent_hist[a][-WINDOW:], agent_hist[b][-WINDOW:]))
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def compute_week_agent_returns(
    week_idx: int,
    week_data: dict,
    market_hist: Dict[str, List[float]],
    p75_vol_4w: float,
) -> tuple[Dict[str, float], Dict[str, float], Dict[str, dict], float, float]:
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

    vol_4w = stdev_last(spy_hist, 4)
    lev = clamp(TARGET_VOL / max(vol_4w, 1e-6), 1.0, 4.0)

    drift_flags: Dict[str, dict] = {}

    mom_8 = 0.6 * mean_last(qqq_hist, 8) + 0.4 * mean_last(spy_hist, 8)
    hb_base = 0.55 * qqq_r + 0.30 * iwm_r + 0.15 * spy_r if mom_8 >= 0 else 0.45 * qqq_r + 0.35 * iwm_r + 0.20 * spy_r

    trend_12 = mean_last(spy_hist, 12)
    lt_base = spy_r if trend_12 >= 0 else 0.65 * agg_r + 0.35 * tlt_r

    carry_gain = 0.0025 if vol_4w < p75_vol_4w else 0.0005
    vol_spike_loss = 5.0 * max(0.0, vol_4w - p75_vol_4w) + 1.4 * max(0.0, -spy_r)
    sv_base = carry_gain - (0.65 * vol_spike_loss)

    spread_calm = mean_last(hyg_hist, 6) - mean_last(agg_hist, 6)
    cc_base = 0.75 * hyg_r + 0.25 * xlf_r if spread_calm >= -0.001 else 0.70 * agg_r + 0.30 * tlt_r

    db_base = 0.55 * agg_r + 0.35 * tlt_r + 0.10 * gld_r
    if vol_4w >= p75_vol_4w:
        db_base += 0.15 * abs(min(spy_r, 0.0))

    returns = {
        "high_beta_momentum": lev * hb_base,
        "leverage_trend": lev * lt_base,
        "short_vol": lev * sv_base,
        "credit_carry": lev * cc_base,
        "defensive_bonds": db_base,
    }

    leverages = {
        "high_beta_momentum": lev,
        "leverage_trend": lev,
        "short_vol": lev,
        "credit_carry": lev,
        "defensive_bonds": 1.0,
    }

    for aid in AGENTS:
        drift_flags[aid] = {"active": aid in RISKY_AGENTS, "reason": "deterministic_leverage" if aid in RISKY_AGENTS else ""}

    avg_lev_risky = sum(leverages[aid] for aid in RISKY_AGENTS) / len(RISKY_AGENTS)
    return returns, leverages, drift_flags, vol_4w, avg_lev_risky


class CascadeExecutor:
    def __init__(self):
        self.ctx_by_week: Dict[int, WeekContext] = {}
        self.delta_hist: Dict[str, List[float]] = {}
        self.agent_ret_hist: Dict[str, List[float]] = {}
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
            self.agent_ret_hist.setdefault(agent.id, []).append(a_ret)
            self.bench_hist.setdefault(agent.id, []).append(b_ret)
            self.last_seen_week[agent.id] = week

        m = rolling_metrics(
            self.delta_hist.get(agent.id, []),
            self.agent_ret_hist.get(agent.id, []),
            self.bench_hist.get(agent.id, []),
        )

        if m["count"] < WINDOW:
            success = True
            outcome = "warmup"
        else:
            risky = agent.id in RISKY_AGENTS
            leverage = ctx.agent_leverage[agent.id]
            fail = (
                (ctx.systemic_corr >= 0.85 and risky and leverage >= 2.5)
                or m["dd_ratio_8w"] >= 1.6
                or m["min_delta_8w"] <= -0.04
            )
            success = not fail
            outcome = "failure" if fail else "success"

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.001,
            metadata={
                "week": week,
                "regime": ctx.regime,
                "delta": round(delta, 6),
                "systemic_corr": round(ctx.systemic_corr, 6),
                "realized_vol_4w": round(ctx.realized_vol_4w, 6),
                "leverage": round(ctx.agent_leverage[agent.id], 4),
                "min_delta_8w": round(m["min_delta_8w"], 6),
                "dd_ratio_8w": round(m["dd_ratio_8w"], 6),
                "signal_class": outcome,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in AGENTS


def build_tasks_for_week(
    week_data: dict,
    week: int,
    returns: Dict[str, float],
    leverages: Dict[str, float],
    systemic_corr: float,
    realized_vol_4w: float,
    p75_vol_4w: float,
) -> List[Task]:
    tasks: List[Task] = []
    bm = float(week_data["benchmark_return"])
    regime = week_data.get("regime", "bull")
    urgency = 0.82 if regime == "stress" else 0.62

    for aid in AGENTS:
        delta = returns[aid] - bm
        impact = 0.25 + 12.0 * abs(delta) + 0.08 * leverages[aid]
        risk = 0.10 + 8.0 * max(0.0, -delta) + 0.08 * leverages[aid]
        if aid in RISKY_AGENTS and systemic_corr >= 0.85 and realized_vol_4w >= p75_vol_4w:
            impact += 0.20
            risk += 0.20
        impact = clamp(impact, 0.10, 1.00)
        risk = clamp(risk, 0.05, 0.50)
        tasks.append(
            Task(
                id=f"CASCADE_{week:03d}_{aid}",
                impact=round(impact, 4),
                urgency=urgency,
                risk=round(risk, 4),
                metadata={
                    "week": week,
                    "date": week_data["date"],
                    "agent": aid,
                    "delta": round(delta, 6),
                    "systemic_corr": round(systemic_corr, 4),
                    "realized_vol_4w": round(realized_vol_4w, 6),
                },
            )
        )
    return tasks


def kernel_status(loop: GovernanceLoop, aid: str) -> str:
    if aid in loop.trust_engine.suppressed_agents:
        return "suppressed"
    if aid in loop.trust_engine.probation_agents:
        return "probation"
    return "active"


def authority_weights(agents: Dict[str, Agent], status_map: Dict[str, str]) -> Dict[str, float]:
    raw = {
        aid: (0.0 if status_map[aid] == "suppressed" else max(agents[aid].trust_score, 0.0))
        for aid in AGENTS
    }
    s = sum(raw.values())
    if s <= 0:
        return {aid: 0.0 for aid in AGENTS}
    return {aid: raw[aid] / s for aid in AGENTS}


def first_week_dd_breach(values: List[float], breach: float = -0.10) -> int | None:
    peak = values[0]
    for i, v in enumerate(values, start=1):
        peak = max(peak, v)
        dd = (v - peak) / peak if peak > 0 else 0.0
        if dd <= breach:
            return i
    return None


def run_cascade_containment() -> dict:
    if not os.path.exists(MARKET_DATA_PATH):
        raise RuntimeError("market_data.json missing. Run: python3 data/fetch_market_data.py")

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks = market_data.get("weeks", [])
    if not weeks:
        raise RuntimeError("No weekly rows in market_data.json")

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

        market_hist: Dict[str, List[float]] = {t: [] for t in weeks[0]["tickers"].keys()}
        for w in weeks:
            for t in market_hist:
                market_hist[t].append(float(w["tickers"][t]["weekly_return"]))

        spy = market_hist["SPY"]
        vol_series = [stdev_last(spy[:i], 4) for i in range(1, len(spy) + 1)]
        vol_sorted = sorted(vol_series)
        p75_vol_4w = vol_sorted[int(0.75 * (len(vol_sorted) - 1))] if vol_sorted else 0.02

        executor = CascadeExecutor()

        gov_val = STARTING_CAPITAL
        ung_val = STARTING_CAPITAL
        bm_val = STARTING_CAPITAL

        gov_peak = gov_val
        ung_peak = ung_val
        bm_peak = bm_val
        gov_max_dd = 0.0
        ung_max_dd = 0.0
        bm_max_dd = 0.0

        peak_systemic_corr = 0.0
        weeks_systemic_corr_above_085 = 0
        peak_leverage_risky = 0.0
        avg_leverage_risky_sum = 0.0
        suppression_events_count = 0

        timeline: List[dict] = []
        events_count = 0
        agent_ret_hist = {aid: [] for aid in AGENTS}
        previous_status = {aid: "active" for aid in AGENTS}
        previous_corr_high = False

        cascade_streak_ung = 0
        cascade_streak_gov = 0
        cascade_prevented_flag = False

        gov_values_track = [gov_val]
        ung_values_track = [ung_val]

        print("\n" + "=" * 80)
        print("  CRISIS 1: SYNCHRONIZED DELEVERAGING CASCADE CONTAINMENT")
        print("=" * 80)

        for idx, w in enumerate(weeks):
            week = int(w["week"])
            date = w["date"]
            regime = w.get("regime", "bull")
            bm_ret = float(w["benchmark_return"])

            returns, leverages, drift_flags, vol_4w, avg_lev_risky = compute_week_agent_returns(
                idx, w, market_hist, p75_vol_4w
            )

            for aid in AGENTS:
                agent_ret_hist[aid].append(returns[aid])
            systemic_corr = systemic_corr_from_hist(agent_ret_hist)

            spiral_on = systemic_corr >= 0.85 and vol_4w >= p75_vol_4w
            spiral_penalty = -SPIRAL_K * vol_4w if spiral_on else 0.0
            if spiral_on:
                for aid in RISKY_AGENTS:
                    returns[aid] += spiral_penalty

            for aid in AGENTS:
                agent_ret_hist[aid][-1] = returns[aid]

            systemic_corr = systemic_corr_from_hist(agent_ret_hist)

            peak_systemic_corr = max(peak_systemic_corr, systemic_corr)
            if systemic_corr >= 0.85:
                weeks_systemic_corr_above_085 += 1

            peak_leverage_risky = max(peak_leverage_risky, max(leverages[aid] for aid in RISKY_AGENTS))
            avg_leverage_risky_sum += avg_lev_risky

            ung_weights = {aid: 1.0 / len(AGENTS) for aid in AGENTS}
            ung_ret = sum(ung_weights[aid] * returns[aid] for aid in AGENTS)

            executor.set_week_context(
                WeekContext(
                    week=week,
                    date=date,
                    regime=regime,
                    benchmark_return=bm_ret,
                    realized_vol_4w=vol_4w,
                    p75_vol_4w=p75_vol_4w,
                    systemic_corr=systemic_corr,
                    agent_returns=returns,
                    agent_leverage=leverages,
                )
            )

            tasks = build_tasks_for_week(
                w, week, returns, leverages, systemic_corr, vol_4w, p75_vol_4w
            )
            agents = registry.get_agents_dict()

            froze = False
            try:
                _ = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"CASCADE_{week:03d}",
                )
            except ValueError as e:
                if "Total of weights must be greater than zero" not in str(e):
                    raise
                froze = True
            except CircuitBreakerTriggered:
                froze = True

            registry.sync_trust_scores()
            agents = registry.get_agents_dict()
            status_map = {aid: kernel_status(loop, aid) for aid in AGENTS}

            weights = authority_weights(agents, status_map)
            if froze:
                weights = {aid: 0.0 for aid in AGENTS}
                if status_map["defensive_bonds"] != "suppressed":
                    weights["defensive_bonds"] = 1.0
                else:
                    weights = {aid: 1.0 / len(AGENTS) for aid in AGENTS}

            gov_ret = sum(weights[aid] * returns[aid] for aid in AGENTS)

            gov_val *= 1.0 + gov_ret
            ung_val *= 1.0 + ung_ret
            bm_val *= 1.0 + bm_ret

            gov_values_track.append(gov_val)
            ung_values_track.append(ung_val)

            gov_peak = max(gov_peak, gov_val)
            ung_peak = max(ung_peak, ung_val)
            bm_peak = max(bm_peak, bm_val)
            gov_max_dd = min(gov_max_dd, (gov_val - gov_peak) / gov_peak)
            ung_max_dd = min(ung_max_dd, (ung_val - ung_peak) / ung_peak)
            bm_max_dd = min(bm_max_dd, (bm_val - bm_peak) / bm_peak)

            week_events: List[dict] = []
            corr_high = systemic_corr >= 0.85
            if corr_high and not previous_corr_high:
                week_events.append(
                    {
                        "type": "systemic_corr_threshold",
                        "color": "amber",
                        "text": f"[WEEK {week:02d}] SYSTEMIC CORR crossed 0.85 ({systemic_corr:.2f})",
                    }
                )

            if spiral_on:
                week_events.append(
                    {
                        "type": "liquidity_spiral",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] Liquidity spiral penalty applied ({spiral_penalty:.4f})",
                    }
                )

            if corr_high and vol_4w >= p75_vol_4w:
                week_events.append(
                    {
                        "type": "safe_degradation_mode",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] SAFE DEGRADATION MODE active",
                    }
                )

            for aid in AGENTS:
                if previous_status[aid] != status_map[aid] and status_map[aid] == "suppressed":
                    suppression_events_count += 1
                    week_events.append(
                        {
                            "type": "suppressed",
                            "color": "red",
                            "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} SUPPRESSED",
                        }
                    )

            events_count += len(week_events)

            ung_cond = corr_high and vol_4w >= p75_vol_4w
            gov_cond = ung_cond and sum(weights[aid] for aid in RISKY_AGENTS) >= 0.70
            cascade_streak_ung = cascade_streak_ung + 1 if ung_cond else 0
            cascade_streak_gov = cascade_streak_gov + 1 if gov_cond else 0
            if cascade_streak_ung >= 3 and cascade_streak_gov < 3:
                cascade_prevented_flag = True

            timeline.append(
                {
                    "week": week,
                    "date": date,
                    "regime": regime,
                    "agents": {
                        aid: {
                            "trust": round(agents[aid].trust_score, 4),
                            "authority_weight": round(weights[aid], 4),
                            "status": status_map[aid],
                            "weekly_return": round(returns[aid], 6),
                            "benchmark_delta": round(returns[aid] - bm_ret, 6),
                            "cumulative_return": round(sum(agent_ret_hist[aid]), 6),
                            "leverage": round(leverages[aid], 4),
                            "drift_flags": drift_flags[aid],
                        }
                        for aid in AGENTS
                    },
                    "portfolio_value": round(gov_val, 0),
                    "benchmark_value": round(bm_val, 0),
                    "portfolio_return": round(gov_ret, 6),
                    "benchmark_return": round(bm_ret, 6),
                    "outperformance_dollar": round(gov_val - bm_val, 0),
                    "outperformance_pct": round((gov_val / bm_val - 1.0) * 100, 2),
                    "ungoverned_portfolio_value": round(ung_val, 0),
                    "ungoverned_return": round(ung_ret, 6),
                    "systemic_corr": round(systemic_corr, 4),
                    "realized_vol_4w": round(vol_4w, 6),
                    "p75_vol_4w": round(p75_vol_4w, 6),
                    "avg_leverage_risky": round(avg_lev_risky, 4),
                    "events": week_events,
                }
            )

            previous_status = status_map
            previous_corr_high = corr_high

            if week % 10 == 0 or week == 1:
                print(
                    f"  Week {week:3d} [{regime:6s}] GOV ${gov_val:>10,.0f} | UNG ${ung_val:>10,.0f} | "
                    f"corr {systemic_corr:.2f} | lev {avg_lev_risky:.2f}"
                )

        avg_leverage_risky = avg_leverage_risky_sum / len(weeks)
        time_to_10pct_dd_ungov = first_week_dd_breach(ung_values_track, breach=-0.10)
        time_to_10pct_dd_gov = first_week_dd_breach(gov_values_track, breach=-0.10)

        summary = {
            "final_governed_value": round(gov_val, 0),
            "final_ungoverned_value": round(ung_val, 0),
            "final_benchmark_value": round(bm_val, 0),
            "max_drawdown_governed": round(gov_max_dd, 4),
            "max_drawdown_ungoverned": round(ung_max_dd, 4),
            "max_drawdown_benchmark": round(bm_max_dd, 4),
            "peak_systemic_corr": round(peak_systemic_corr, 4),
            "weeks_systemic_corr_above_085": weeks_systemic_corr_above_085,
            "peak_leverage_risky": round(peak_leverage_risky, 4),
            "avg_leverage_risky": round(avg_leverage_risky, 4),
            "suppression_events_count": suppression_events_count,
            "time_to_10pct_dd_ungov": time_to_10pct_dd_ungov,
            "time_to_10pct_dd_gov": time_to_10pct_dd_gov,
            "cascade_prevented_flag": cascade_prevented_flag,
            "governance_events_count": events_count,
            # compatibility keys
            "final_portfolio_value": round(gov_val, 0),
            "final_benchmark_value": round(bm_val, 0),
            "total_outperformance_pct": round((gov_val / bm_val - 1.0) * 100, 2),
            "total_outperformance_pct_ungov_vs_bm": round((ung_val / bm_val - 1.0) * 100, 2),
            "total_outperformance_pct_gov_vs_ungov": round((gov_val / ung_val - 1.0) * 100, 2) if ung_val > 0 else None,
            "benchmark": "60% SPY / 40% AGG",
            "data_source": "yfinance (real)",
            "total_weeks": len(timeline),
            "sleeves": list(AGENTS.keys()),
        }

        out = {"summary": summary, "timeline": timeline}
        with open(OUTPUT_PATH, "w") as f:
            json.dump(out, f, indent=2)

        print("\n" + "=" * 80)
        print("  CRISIS 1 COMPLETE")
        print("=" * 80)
        print(f"  GOV value: ${gov_val:,.0f}")
        print(f"  UNG value: ${ung_val:,.0f}")
        print(f"  BM  value: ${bm_val:,.0f}")
        print(f"  DD GOV/UNG/BM: {gov_max_dd:.2%}/{ung_max_dd:.2%}/{bm_max_dd:.2%}")
        print(f"  Peak systemic corr: {peak_systemic_corr:.2f} | weeks>=0.85: {weeks_systemic_corr_above_085}")
        print(f"  Peak/avg risky leverage: {peak_leverage_risky:.2f}x/{avg_leverage_risky:.2f}x")
        print(f"  Suppressions: {suppression_events_count}")
        print(f"  Cascade prevented flag: {cascade_prevented_flag}")
        print(f"  Output: {OUTPUT_PATH}")

        return out

    finally:
        state.close()


if __name__ == "__main__":
    run_cascade_containment()
