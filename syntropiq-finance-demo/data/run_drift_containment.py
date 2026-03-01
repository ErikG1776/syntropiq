#!/usr/bin/env python3
"""
Finance Drift Containment Demo

Demonstrates governed vs ungoverned autonomous strategies on identical real market data.
Kernel code remains unchanged; this is a wrapper-only simulation.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# repo root for Syntropiq imports when run from syntropiq-finance-demo/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")
DB_PATH = os.path.join(DATA_DIR, "finance_drift_demo.db")

STARTING_PORTFOLIO = 10_000_000.0
INITIAL_TRUST = 0.75

INITIAL_TRUST_THRESHOLD = 0.70
INITIAL_SUPPRESSION_THRESHOLD = 0.75
INITIAL_DRIFT_DELTA = 0.10
ROUTING_MODE = "deterministic"

WINDOW = 8
EPS = 1e-9
BENCHMARK_LABEL = "60% SPY / 40% AGG"

LENDING_PAYLOAD_REFERENCE = {
    "task": {
        "id": "LOAN_2847",
        "impact": 0.72,
        "urgency": 0.85,
        "risk": 0.45,
        "metadata": {
            "amount": 25000,
            "grade": "C",
            "dti": 18.5,
            "purpose": "debt_consolidation",
        },
    },
    "result": {
        "task_id": "LOAN_2847",
        "agent_id": "growth_underwriter",
        "success": False,
        "metadata": {
            "decision": "APPROVED",
            "outcome": "DEFAULTED",
            "risk_score": 0.45,
            "loss_amount": 8200,
        },
    },
    "governance_response": {
        "trust_update": {"growth_underwriter": 0.71},
        "status": "probation",
        "mutation": {"trust_threshold": 0.73},
    },
}

AGENTS: Dict[str, Dict] = {
    "trend_following": {"label": "Trend Following"},
    "vol_target": {"label": "Vol Target"},
    "carry_credit": {"label": "Carry Credit"},
    "momentum": {"label": "Momentum"},
    "defensive": {"label": "Defensive"},
    "value_rotation": {"label": "Value Rotation"},
    "macro_parity": {"label": "Macro Parity"},
    "mean_reversion": {"label": "Mean Reversion"},
}

DRIFTED_AGENTS = {"trend_following", "vol_target"}


@dataclass
class WeekContext:
    week: int
    date: str
    regime: str
    benchmark_return: float
    portfolio_value_before: float
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


def weighted_return(current: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(weights.get(t, 0.0) * current.get(t, 0.0) for t in weights)


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


def structural_metrics(deltas: List[float], agent_rets: List[float], bench_rets: List[float]) -> Dict[str, float]:
    d = deltas[-WINDOW:]
    a = agent_rets[-WINDOW:]
    b = bench_rets[-WINDOW:]

    if not d:
        return {
            "count": 0,
            "alpha_8w": 0.0,
            "min_delta_8w": 0.0,
            "tracking_error_8w": 0.0,
            "dd_agent_8w": 0.0,
            "dd_bench_8w": 0.0,
            "dd_ratio": 0.0,
        }

    alpha = sum(d) / len(d)
    min_delta = min(d)
    te = statistics.pstdev(d) if len(d) > 1 else 0.0
    dd_agent = max_drawdown_from_returns(a)
    dd_bench = max_drawdown_from_returns(b)
    dd_ratio = dd_agent / max(dd_bench, EPS)

    return {
        "count": len(d),
        "alpha_8w": alpha,
        "min_delta_8w": min_delta,
        "tracking_error_8w": te,
        "dd_agent_8w": dd_agent,
        "dd_bench_8w": dd_bench,
        "dd_ratio": dd_ratio,
    }


def build_history_by_ticker(weeks: List[dict]) -> Dict[str, List[float]]:
    tickers = list(weeks[0]["tickers"].keys())
    out = {t: [] for t in tickers}
    for w in weeks:
        for t in tickers:
            out[t].append(float(w["tickers"][t]["weekly_return"]))
    return out


def compute_strategy_return(
    agent_id: str,
    idx: int,
    week_data: dict,
    hist: Dict[str, List[float]],
    drift_start_week: int,
    spy_vol_p75: float,
) -> Tuple[float, bool, str]:
    current = {t: float(v["weekly_return"]) for t, v in week_data["tickers"].items()}
    prev = {t: hist[t][:idx] for t in hist}

    spy_prev = prev["SPY"]
    qqq_prev = prev["QQQ"]
    agg_prev = prev["AGG"]
    tlt_prev = prev["TLT"]
    hyg_prev = prev["HYG"]
    xlf_prev = prev["XLF"]
    iwm_prev = prev["IWM"]
    gld_prev = prev["GLD"]

    drift_active = False
    drift_reason = ""
    week = idx + 1

    if agent_id == "trend_following":
        trend_12 = mean_last(spy_prev, 12)
        threshold = 0.002
        # deterministic parameter creep after regime shift
        if week >= drift_start_week:
            drift_active = True
            drift_reason = "parameter_creep"
            threshold += min(0.03, 0.00045 * (week - drift_start_week + 1))

        # higher threshold means slower de-risking => stays risk-on too long
        risk_off_trigger = -threshold
        if trend_12 < risk_off_trigger:
            w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.20}
        else:
            if drift_active:
                # Drifted policy remains risk-on too long with a fragile mix.
                w = {"QQQ": 0.55, "IWM": 0.25, "USO": 0.20}
            else:
                w = {"SPY": 0.45, "QQQ": 0.35, "IWM": 0.20}
        ret = weighted_return(current, w)

    elif agent_id == "vol_target":
        vol4 = stdev_last(spy_prev, 4)
        risk_on = 0.50 * current["SPY"] + 0.30 * current["QQQ"] + 0.15 * current["IWM"] + 0.05 * current["USO"]
        safe = 0.60 * current["AGG"] + 0.30 * current["TLT"] + 0.10 * current["GLD"]

        exposure = clamp(0.011 / max(vol4, 1e-6), 0.30, 1.25)

        # deterministic correlation/vol sensitivity breakdown
        if vol4 > spy_vol_p75:
            drift_active = True
            drift_reason = "correlation_breakdown_sensitivity"
            exposure = clamp(exposure * 1.6, 0.60, 2.20)  # wrong-way under stress

        ret = safe + exposure * (risk_on - safe)

    elif agent_id == "carry_credit":
        carry = mean_last(hyg_prev, 6) - mean_last(agg_prev, 6)
        if carry > 0:
            w = {"HYG": 0.55, "SPY": 0.25, "AGG": 0.20}
        else:
            w = {"AGG": 0.55, "TLT": 0.30, "GLD": 0.15}
        ret = weighted_return(current, w)

    elif agent_id == "momentum":
        m = 0.5 * mean_last(spy_prev, 8) + 0.5 * mean_last(qqq_prev, 8)
        if m > 0:
            w = {"QQQ": 0.50, "SPY": 0.35, "IWM": 0.15}
        else:
            w = {"AGG": 0.55, "TLT": 0.30, "GLD": 0.15}
        ret = weighted_return(current, w)

    elif agent_id == "defensive":
        vol8 = stdev_last(spy_prev, 8)
        if vol8 > spy_vol_p75:
            w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.20}
        else:
            w = {"AGG": 0.40, "TLT": 0.25, "GLD": 0.15, "SPY": 0.20}
        ret = weighted_return(current, w)

    elif agent_id == "value_rotation":
        value_mom = 0.5 * mean_last(xlf_prev, 6) + 0.5 * mean_last(iwm_prev, 6)
        growth_mom = mean_last(qqq_prev, 6)
        if value_mom > growth_mom:
            w = {"XLF": 0.40, "IWM": 0.35, "SPY": 0.25}
        else:
            w = {"QQQ": 0.45, "SPY": 0.35, "AGG": 0.20}
        ret = weighted_return(current, w)

    elif agent_id == "macro_parity":
        vols = {
            "SPY": stdev_last(spy_prev, 12),
            "TLT": stdev_last(tlt_prev, 12),
            "GLD": stdev_last(gld_prev, 12),
            "EEM": stdev_last(prev["EEM"], 12),
        }
        inv = {k: 1.0 / max(v, 1e-6) for k, v in vols.items()}
        total_inv = sum(inv.values())
        weights = {k: inv[k] / total_inv for k in inv}
        ret = weighted_return(current, weights)

    elif agent_id == "mean_reversion":
        last_spy = spy_prev[-1] if spy_prev else 0.0
        if last_spy < -0.015:
            w = {"SPY": 0.45, "IWM": 0.30, "QQQ": 0.15, "AGG": 0.10}
        elif last_spy > 0.015:
            w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.20}
        else:
            w = {"SPY": 0.30, "AGG": 0.35, "QQQ": 0.20, "GLD": 0.15}
        ret = weighted_return(current, w)

    else:
        ret = 0.0

    return ret, drift_active, drift_reason


class DriftContainmentExecutor:
    """Maps strategy outcomes to structural success/failure for kernel governance."""

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

        m = structural_metrics(
            self.delta_hist.get(agent.id, []),
            self.agent_hist.get(agent.id, []),
            self.bench_hist.get(agent.id, []),
        )

        if m["count"] < WINDOW:
            success = True
            signal_class = "warmup"
        else:
            structural_failure = (
                m["alpha_8w"] <= -0.010
                or m["min_delta_8w"] <= -0.035
                or (m["dd_ratio"] >= 1.5 and m["dd_agent_8w"] > m["dd_bench_8w"])
            )
            if structural_failure:
                success = False
                signal_class = "failure"
            else:
                success = True
                signal_class = "success"

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.001,
            metadata={
                "weekly_return": round(a_ret, 6),
                "benchmark_return": round(b_ret, 6),
                "delta": round(delta, 6),
                "alpha_8w": round(m["alpha_8w"], 6),
                "min_delta_8w": round(m["min_delta_8w"], 6),
                "tracking_error_8w": round(m["tracking_error_8w"], 6),
                "dd_agent_8w": round(m["dd_agent_8w"], 6),
                "dd_bench_8w": round(m["dd_bench_8w"], 6),
                "dd_ratio": round(m["dd_ratio"], 6),
                "signal_class": signal_class,
                "week": week,
                "regime": ctx.regime,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in AGENTS


def build_tasks_for_week(
    week_data: dict,
    agent_returns: Dict[str, float],
    delta_hist: Dict[str, List[float]],
    agent_hist: Dict[str, List[float]],
    bench_hist: Dict[str, List[float]],
) -> List[Task]:
    week = int(week_data["week"])
    date = week_data["date"]
    regime = week_data.get("regime", "bull")
    bench = float(week_data["benchmark_return"])

    urgency = 0.78 if regime == "stress" else 0.60
    tasks: List[Task] = []

    for aid in AGENTS:
        delta = agent_returns[aid] - bench
        m = structural_metrics(
            delta_hist.get(aid, []) + [delta],
            agent_hist.get(aid, []) + [agent_returns[aid]],
            bench_hist.get(aid, []) + [bench],
        )
        alpha = m["alpha_8w"]
        risk = clamp(0.08 + 10.0 * max(0.0, -alpha), 0.05, 0.35)
        impact = clamp(0.30 + 60.0 * abs(alpha), 0.10, 1.00)

        tasks.append(
            Task(
                id=f"DRIFT_{week:03d}_{aid}",
                impact=round(impact, 4),
                urgency=urgency,
                risk=round(risk, 4),
                metadata={
                    "week": week,
                    "date": date,
                    "regime": regime,
                    "agent": aid,
                    "delta": round(delta, 6),
                    "alpha_8w": round(m["alpha_8w"], 6),
                    "tracking_error_8w": round(m["tracking_error_8w"], 6),
                    "dd_agent_8w": round(m["dd_agent_8w"], 6),
                    "dd_bench_8w": round(m["dd_bench_8w"], 6),
                    "dd_ratio": round(m["dd_ratio"], 6),
                    "min_delta_8w": round(m["min_delta_8w"], 6),
                },
            )
        )

    return tasks


def agent_status_from_kernel(loop: GovernanceLoop, agent: Agent) -> str:
    if agent.id in loop.trust_engine.suppressed_agents:
        return "suppressed"
    if agent.id in loop.trust_engine.probation_agents:
        return "probation"
    return "active"


def authority_weights_from_trust(agents, status_map):
    raw = {}
    for aid in AGENTS:
        if status_map[aid] == "suppressed":
            raw[aid] = 0.0
        else:
            raw[aid] = max(0.0, agents[aid].trust_score)

    total = sum(raw.values())
    if total <= 0:
        return {aid: 0.0 for aid in AGENTS}
    return {aid: raw[aid] / total for aid in AGENTS}


def run_drift_containment() -> dict:
    if not os.path.exists(MARKET_DATA_PATH):
        raise RuntimeError("market_data.json missing. Run: python3 data/fetch_market_data.py")

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks = market_data.get("weeks", [])
    if not weeks:
        raise RuntimeError("No weekly rows found in market_data.json")

    drift_start_week = int(market_data.get("regime_shift_week") or 53)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    state = PersistentStateManager(db_path=DB_PATH)

    try:
        registry = AgentRegistry(state)
        for aid in AGENTS:
            registry.register_agent(
                agent_id=aid,
                capabilities=["allocation", "strategy_signal"],
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
        # Wrapper-level operating point tuning only (kernel logic unchanged)
        loop.mutation_engine.mutation_rate = 0.003
        loop.mutation_engine.target_success_rate = 0.70
        loop.trust_engine.MAX_REDEMPTION_CYCLES = 200

        executor = DriftContainmentExecutor()

        # deterministic volatility threshold from history
        ticker_hist = build_history_by_ticker(weeks)
        spy_vol_series = [stdev_last(ticker_hist["SPY"][:i], 4) for i in range(1, len(weeks) + 1)]
        vol_sorted = sorted(spy_vol_series)
        spy_vol_p75 = vol_sorted[int(0.75 * (len(vol_sorted) - 1))] if vol_sorted else 0.02

        governed_value = STARTING_PORTFOLIO
        ungoverned_value = STARTING_PORTFOLIO
        benchmark_value = STARTING_PORTFOLIO

        peak_gov = governed_value
        peak_ung = ungoverned_value
        peak_bm = benchmark_value
        max_dd_gov = 0.0
        max_dd_ung = 0.0
        max_dd_bm = 0.0

        drift_only_gov_value = STARTING_PORTFOLIO
        drift_only_ung_value = STARTING_PORTFOLIO

        timeline: List[dict] = []
        all_events: List[dict] = []

        delta_hist = {aid: [] for aid in AGENTS}
        agent_hist = {aid: [] for aid in AGENTS}
        bench_hist = {aid: [] for aid in AGENTS}
        cumulative_returns = {aid: 0.0 for aid in AGENTS}
        weeks_suppressed = {aid: 0 for aid in AGENTS}

        previous_status = {aid: "active" for aid in AGENTS}
        previous_mutation = {
            "trust_threshold": INITIAL_TRUST_THRESHOLD,
            "suppression_threshold": INITIAL_SUPPRESSION_THRESHOLD,
            "drift_delta": INITIAL_DRIFT_DELTA,
        }

        drift_windows_detected = 0
        governed_drift_exposure_weeks = 0

        sample_finance_payload = None

        print("\n" + "=" * 84)
        print("  FINANCE DRIFT CONTAINMENT")
        print("  Governed vs Ungoverned Autonomous Strategies")
        print("=" * 84)

        for i, w in enumerate(weeks):
            week = int(w["week"])
            date = w["date"]
            regime = w.get("regime", "bull")
            bench_ret = float(w["benchmark_return"])

            week_events: List[dict] = []

            # strategy returns + deterministic drift flags
            agent_returns: Dict[str, float] = {}
            drift_flags: Dict[str, dict] = {}
            for aid in AGENTS:
                r, drift_active, drift_reason = compute_strategy_return(
                    aid,
                    i,
                    w,
                    ticker_hist,
                    drift_start_week,
                    spy_vol_p75,
                )
                agent_returns[aid] = r
                drift_flags[aid] = {"active": drift_active, "reason": drift_reason}

            drift_week_active = any(drift_flags[aid]["active"] for aid in DRIFTED_AGENTS)
            if drift_week_active:
                drift_windows_detected += 1

            # UNGOVERNED baseline
            ungoverned_ret = sum(agent_returns.values()) / len(AGENTS)

            executor.set_week_context(
                WeekContext(
                    week=week,
                    date=date,
                    regime=regime,
                    benchmark_return=bench_ret,
                    portfolio_value_before=governed_value,
                    agent_returns=agent_returns,
                )
            )

            tasks = build_tasks_for_week(w, agent_returns, delta_hist, agent_hist, bench_hist)

            agents = registry.get_agents_dict()
            trust_before = {aid: agents[aid].trust_score for aid in AGENTS}

            froze_this_week = False
            try:
                result = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"DRIFT_{week:03d}",
                )
            except ValueError as e:
                if "Total of weights must be greater than zero" not in str(e):
                    raise
                froze_this_week = True
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] ROUTING FREEZE — no eligible sleeves; governed held in benchmark",
                    }
                )
                result = {
                    "run_id": f"DRIFT_{week:03d}_freeze",
                    "results": [],
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {
                        "tasks_executed": 0,
                        "successes": 0,
                        "failures": 0,
                        "avg_latency": 0.0,
                    },
                }
            except CircuitBreakerTriggered as e:
                froze_this_week = True
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] GOVERNANCE HALT — {str(e)}; governed held in benchmark",
                    }
                )
                result = {
                    "run_id": f"DRIFT_{week:03d}_halt",
                    "results": [],
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {
                        "tasks_executed": 0,
                        "successes": 0,
                        "failures": 0,
                        "avg_latency": 0.0,
                    },
                }
            except RuntimeError as e:
                if "No trusted agents available" not in str(e):
                    raise
                froze_this_week = True
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] GOVERNANCE HALT — no trusted sleeves; governed held in benchmark",
                    }
                )
                result = {
                    "run_id": f"DRIFT_{week:03d}_halt",
                    "results": [],
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {
                        "tasks_executed": 0,
                        "successes": 0,
                        "failures": 0,
                        "avg_latency": 0.0,
                    },
                }

            registry.sync_trust_scores()
            agents = registry.get_agents_dict()

            status_map = {aid: agent_status_from_kernel(loop, agents[aid]) for aid in AGENTS}
            weights = authority_weights_from_trust(agents, status_map)

            if froze_this_week:
                governed_ret = bench_ret
                weights = {aid: 0.0 for aid in AGENTS}
            else:
                governed_ret = sum(weights[aid] * agent_returns[aid] for aid in AGENTS)

            # trust and lifecycle events
            for aid, new_trust in result.get("trust_updates", {}).items():
                old = trust_before.get(aid, new_trust)
                dt = new_trust - old
                rel = agent_returns[aid] - bench_ret
                if dt > 0:
                    week_events.append(
                        {
                            "type": "trust_increase",
                            "color": "blue",
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} delta {rel:+.2%} — "
                                f"trust ↑ {old:.2f} → {new_trust:.2f}"
                            ),
                        }
                    )
                elif dt < 0:
                    week_events.append(
                        {
                            "type": "trust_decrease",
                            "color": "amber",
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} delta {rel:+.2%} — "
                                f"trust ↓ {old:.2f} → {new_trust:.2f}"
                            ),
                        }
                    )

            for aid in AGENTS:
                prev = previous_status[aid]
                curr = status_map[aid]
                if curr == "suppressed":
                    weeks_suppressed[aid] += 1
                if curr != prev:
                    if curr == "suppressed":
                        week_events.append(
                            {
                                "type": "suppressed",
                                "color": "red",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} SUPPRESSED",
                            }
                        )
                    elif curr == "probation":
                        week_events.append(
                            {
                                "type": "probation",
                                "color": "amber",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} → PROBATION",
                            }
                        )
                    elif prev == "suppressed" and curr in {"probation", "active"}:
                        week_events.append(
                            {
                                "type": "redeemed",
                                "color": "green",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} REDEEMED to {curr.upper()}",
                            }
                        )

            mutation = result.get("mutation", previous_mutation)
            if abs(mutation["suppression_threshold"] - previous_mutation["suppression_threshold"]) > 1e-12:
                week_events.append(
                    {
                        "type": "mutation",
                        "color": "purple",
                        "text": (
                            f"[WEEK {week:02d}] THRESHOLD MUTATION — suppression "
                            f"{previous_mutation['suppression_threshold']:.2f} → {mutation['suppression_threshold']:.2f}"
                        ),
                    }
                )
            previous_mutation = mutation

            # update values
            governed_value *= 1.0 + governed_ret
            ungoverned_value *= 1.0 + ungoverned_ret
            benchmark_value *= 1.0 + bench_ret

            if drift_week_active:
                drift_only_gov_value *= 1.0 + governed_ret
                drift_only_ung_value *= 1.0 + ungoverned_ret

            peak_gov = max(peak_gov, governed_value)
            peak_ung = max(peak_ung, ungoverned_value)
            peak_bm = max(peak_bm, benchmark_value)
            max_dd_gov = min(max_dd_gov, (governed_value - peak_gov) / peak_gov)
            max_dd_ung = min(max_dd_ung, (ungoverned_value - peak_ung) / peak_ung)
            max_dd_bm = min(max_dd_bm, (benchmark_value - peak_bm) / peak_bm)

            for aid in AGENTS:
                delta = agent_returns[aid] - bench_ret
                delta_hist[aid].append(delta)
                agent_hist[aid].append(agent_returns[aid])
                bench_hist[aid].append(bench_ret)
                cumulative_returns[aid] += agent_returns[aid]

            drifted_weight_exposure = max(
                (weights.get(aid, 0.0) for aid in DRIFTED_AGENTS if drift_flags[aid]["active"]),
                default=0.0,
            )
            if drifted_weight_exposure > 0.20:
                governed_drift_exposure_weeks += 1

            if week == 1:
                ex = "trend_following"
                ex_delta = agent_returns[ex] - bench_ret
                sample_finance_payload = {
                    "task": {
                        "id": f"DRIFT_{week:03d}_{ex}",
                        "impact": round(tasks[0].impact, 3),
                        "urgency": round(tasks[0].urgency, 3),
                        "risk": round(tasks[0].risk, 3),
                        "metadata": {
                            "weekly_return": round(agent_returns[ex], 6),
                            "benchmark_delta": round(ex_delta, 6),
                            "regime": regime,
                            "strategy": ex,
                        },
                    },
                    "result": {
                        "task_id": f"DRIFT_{week:03d}_{ex}",
                        "agent_id": ex,
                        "success": ex_delta >= 0,
                        "metadata": {
                            "decision": "OUTPERFORMED" if ex_delta >= 0 else "UNDERPERFORMED",
                            "outcome": "ALPHA_GENERATED" if ex_delta >= 0 else "STRUCTURAL_MISALIGNMENT",
                            "benchmark_delta": round(ex_delta, 6),
                            "authority_weight": round(weights[ex], 4),
                        },
                    },
                    "governance_response": {
                        "trust_update": {ex: round(agents[ex].trust_score, 3)},
                        "status": status_map[ex],
                        "mutation": {"suppression_threshold": round(mutation["suppression_threshold"], 3)},
                    },
                }

            week_record = {
                "week": week,
                "date": date,
                "regime": regime,
                "agents": {},
                # existing UI fields
                "portfolio_value": round(governed_value, 0),
                "benchmark_value": round(benchmark_value, 0),
                "portfolio_return": round(governed_ret, 6),
                "benchmark_return": round(bench_ret, 6),
                "outperformance_dollar": round(governed_value - benchmark_value, 0),
                "outperformance_pct": round((governed_value - benchmark_value) / STARTING_PORTFOLIO * 100, 2),
                "events": week_events,
                "regime_shift": week == drift_start_week,
                "suppression_floor": round(mutation["suppression_threshold"], 3),
                "max_drawdown_portfolio": round(max_dd_gov, 4),
                "max_drawdown_benchmark": round(max_dd_bm, 4),
                # added safe extras
                "governed_portfolio_value": round(governed_value, 0),
                "ungoverned_portfolio_value": round(ungoverned_value, 0),
                "governed_return": round(governed_ret, 6),
                "ungoverned_return": round(ungoverned_ret, 6),
                "outperformance_dollar_ungov_vs_bm": round(ungoverned_value - benchmark_value, 0),
                "outperformance_dollar_gov_vs_ungov": round(governed_value - ungoverned_value, 0),
                "max_drawdown_ungoverned": round(max_dd_ung, 4),
                "drift_flags": drift_flags,
            }

            for aid in AGENTS:
                week_record["agents"][aid] = {
                    "trust": round(agents[aid].trust_score, 4),
                    "authority_weight": round(weights[aid], 4),
                    "status": status_map[aid],
                    "weekly_return": round(agent_returns[aid], 6),
                    "benchmark_delta": round(agent_returns[aid] - bench_ret, 6),
                    "cumulative_return": round(cumulative_returns[aid], 6),
                }

            timeline.append(week_record)
            all_events.extend(week_events)
            previous_status = status_map

            if week % 10 == 0 or week == 1:
                print(
                    f"  Week {week:3d} [{regime:6s}] GOV ${governed_value:>11,.0f} | "
                    f"UNG ${ungoverned_value:>11,.0f} | BM ${benchmark_value:>11,.0f}"
                )

        governance_events_count = len(all_events)
        prevented_loss_during_drift = drift_only_ung_value - drift_only_gov_value

        summary = {
            "final_portfolio_value": round(governed_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "final_ungoverned_value": round(ungoverned_value, 0),
            "total_outperformance_pct": round((governed_value / benchmark_value - 1.0) * 100, 2),
            "total_outperformance_pct_ungov_vs_bm": round((ungoverned_value / benchmark_value - 1.0) * 100, 2),
            "total_outperformance_pct_gov_vs_ungov": round((governed_value / ungoverned_value - 1.0) * 100, 2),
            "max_drawdown_governed": round(max_dd_gov, 4),
            "max_drawdown_ungoverned": round(max_dd_ung, 4),
            "max_drawdown_benchmark": round(max_dd_bm, 4),
            "drift_windows_detected": drift_windows_detected,
            "governed_drift_exposure_weeks": governed_drift_exposure_weeks,
            "ungoverned_drift_exposure_weeks": drift_windows_detected,
            "prevented_loss_during_drift": round(prevented_loss_during_drift, 2),
            "governance_events_count": governance_events_count,
            "benchmark": BENCHMARK_LABEL,
            "data_source": "yfinance (real)",
            "starting_portfolio": STARTING_PORTFOLIO,
            "total_weeks": len(timeline),
            "sleeves": list(AGENTS.keys()),
            "payload_comparison": {
                "finance": sample_finance_payload,
                "lending": LENDING_PAYLOAD_REFERENCE,
            },
            # compatibility keys expected by current UI components
            "total_outperformance_dollar": round(governed_value - benchmark_value, 0),
            "final_governed_value": round(governed_value, 0),
            "total_governance_events": governance_events_count,
        }

        for aid, count in weeks_suppressed.items():
            summary[f"weeks_{aid}_suppressed"] = count

        output = {
            "summary": summary,
            "timeline": timeline,
        }

        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        print("\n" + "=" * 84)
        print("  DRIFT CONTAINMENT COMPLETE")
        print("=" * 84)
        print(f"  GOV value: ${governed_value:,.0f}")
        print(f"  UNG value: ${ungoverned_value:,.0f}")
        print(f"  BM  value: ${benchmark_value:,.0f}")
        print(f"  GOV vs UNG alpha: {(governed_value / ungoverned_value - 1.0) * 100:+.2f}%")
        print(
            f"  Drawdowns: GOV {max_dd_gov:.2%} | UNG {max_dd_ung:.2%} | BM {max_dd_bm:.2%}"
        )
        print(
            "  Drift exposure reduction: "
            f"{drift_windows_detected - governed_drift_exposure_weeks} weeks "
            f"({drift_windows_detected} -> {governed_drift_exposure_weeks})"
        )
        print(f"  Output: {OUTPUT_PATH}")

        return output

    finally:
        state.close()


if __name__ == "__main__":
    run_drift_containment()
