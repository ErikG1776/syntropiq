#!/usr/bin/env python3
"""
Governed vs Ungoverned Autonomous Finance meta-layer demo.

Uses real market data and the existing Syntropiq kernel unchanged.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# repo root for Syntropiq imports when run from syntropiq-finance-demo/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")
UNGOV_OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data_ungoverned.json")
DB_PATH = os.path.join(DATA_DIR, "finance_meta_demo.db")

STARTING_PORTFOLIO = 10_000_000
INITIAL_TRUST = 0.75

INITIAL_TRUST_THRESHOLD = 0.70
INITIAL_SUPPRESSION_THRESHOLD = 0.75
INITIAL_DRIFT_DELTA = 0.10
ROUTING_MODE = "competitive"

BENCHMARK_LABEL = "60% SPY / 40% AGG"
WINDOW = 8

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
    "momentum": {"label": "Momentum"},
    "mean_reversion": {"label": "Mean Reversion"},
    "vol_target": {"label": "Vol Target"},
    "trend": {"label": "Trend"},
    "credit_carry": {"label": "Credit Carry"},
    "value": {"label": "Value Rotation"},
    "macro": {"label": "Macro Parity"},
    "defensive": {"label": "Defensive"},
}


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


def mix(current: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(weights.get(t, 0.0) * current.get(t, 0.0) for t in weights)


def max_drawdown_from_returns(returns: List[float]) -> float:
    if not returns:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= 1.0 + r
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def structural_metrics(delta_hist: List[float], agent_hist: List[float], bench_hist: List[float]) -> Dict[str, float]:
    d = delta_hist[-WINDOW:]
    a = agent_hist[-WINDOW:]
    b = bench_hist[-WINDOW:]
    if not d:
        return {
            "count": 0,
            "alpha_8w": 0.0,
            "tracking_error_8w": 0.0,
            "dd_agent_8w": 0.0,
            "dd_bench_8w": 0.0,
            "dd_ratio": 0.0,
            "min_delta_8w": 0.0,
        }

    alpha = sum(d) / len(d)
    te = statistics.pstdev(d) if len(d) > 1 else 0.0
    dd_agent = max_drawdown_from_returns(a)
    dd_bench = max_drawdown_from_returns(b)
    dd_ratio = dd_agent / max(dd_bench, 1e-9)
    min_delta = min(d)

    return {
        "count": len(d),
        "alpha_8w": alpha,
        "tracking_error_8w": te,
        "dd_agent_8w": dd_agent,
        "dd_bench_8w": dd_bench,
        "dd_ratio": dd_ratio,
        "min_delta_8w": min_delta,
    }


def build_return_history(weeks: List[dict]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    tickers = list(weeks[0]["tickers"].keys())
    for t in tickers:
        out[t] = []
    for w in weeks:
        for t in tickers:
            out[t].append(float(w["tickers"][t]["weekly_return"]))
    return out


def compute_agent_week_return(
    agent_id: str,
    week_idx: int,
    week_data: dict,
    hist: Dict[str, List[float]],
    spy_vol_threshold: float,
) -> Tuple[float, bool, str]:
    current = {t: float(v["weekly_return"]) for t, v in week_data["tickers"].items()}

    # history up to prior week
    prev = {t: hist[t][:week_idx] for t in hist}
    spy_prev = prev["SPY"]
    qqq_prev = prev["QQQ"]
    agg_prev = prev["AGG"]
    tlt_prev = prev["TLT"]
    hyg_prev = prev["HYG"]
    xlf_prev = prev["XLF"]
    iwm_prev = prev["IWM"]

    drifted = False
    drift_reason = ""

    if agent_id == "momentum":
        m = (mean_last(spy_prev, 8) + mean_last(qqq_prev, 8)) / 2.0
        w = {"QQQ": 0.6, "SPY": 0.4} if m > 0 else {"AGG": 0.6, "TLT": 0.4}
        r = mix(current, w)

    elif agent_id == "mean_reversion":
        last_spy = spy_prev[-1] if spy_prev else 0.0
        if last_spy < -0.01:
            w = {"SPY": 0.45, "IWM": 0.25, "QQQ": 0.2, "AGG": 0.1}
        elif last_spy > 0.01:
            w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.2}
        else:
            w = {"SPY": 0.3, "AGG": 0.4, "QQQ": 0.2, "GLD": 0.1}
        r = mix(current, w)

    elif agent_id == "vol_target":
        spy_vol4 = stdev_last(spy_prev, 4)
        base = 0.55 * current["SPY"] + 0.25 * current["QQQ"] + 0.2 * current["IWM"]
        safe = 0.6 * current["AGG"] + 0.3 * current["TLT"] + 0.1 * current["GLD"]

        exposure = clamp(0.012 / max(spy_vol4, 1e-6), 0.25, 1.35)

        # Drift injection B: correlation-break sensitivity under vol spikes.
        if spy_vol4 > spy_vol_threshold:
            drifted = True
            drift_reason = "correlation_break_sensitivity"
            exposure = clamp(exposure * 1.35, 0.4, 1.7)  # wrong-way risk increase

        r = exposure * base + (1.0 - min(exposure, 1.0)) * safe

    elif agent_id == "trend":
        trend_12 = mean_last(spy_prev, 12)
        threshold = 0.0

        # Drift injection A: parameter creep after week 53.
        if week_idx + 1 >= 53:
            drifted = True
            drift_reason = "parameter_creep"
            threshold = min(0.012, 0.0003 * ((week_idx + 1) - 52))

        if trend_12 > threshold:
            w = {"SPY": 0.45, "QQQ": 0.35, "IWM": 0.2}
        else:
            w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.2}
        r = mix(current, w)

    elif agent_id == "credit_carry":
        carry = mean_last(hyg_prev, 6) - mean_last(agg_prev, 6)
        if carry > 0:
            w = {"HYG": 0.55, "SPY": 0.25, "AGG": 0.2}
        else:
            w = {"AGG": 0.6, "TLT": 0.25, "GLD": 0.15}
        r = mix(current, w)

    elif agent_id == "value":
        val = (mean_last(xlf_prev, 6) + mean_last(iwm_prev, 6)) / 2.0
        growth = mean_last(qqq_prev, 6)
        if val > growth:
            w = {"XLF": 0.4, "IWM": 0.35, "SPY": 0.25}
        else:
            w = {"QQQ": 0.5, "SPY": 0.3, "AGG": 0.2}
        r = mix(current, w)

    elif agent_id == "macro":
        vol_spy = stdev_last(spy_prev, 12)
        vol_tlt = stdev_last(tlt_prev, 12)
        vol_gld = stdev_last(prev["GLD"], 12)
        inv = {
            "SPY": 1.0 / max(vol_spy, 1e-6),
            "TLT": 1.0 / max(vol_tlt, 1e-6),
            "GLD": 1.0 / max(vol_gld, 1e-6),
        }
        total_inv = sum(inv.values())
        w = {k: v / total_inv for k, v in inv.items()} if total_inv > 0 else {"SPY": 0.4, "TLT": 0.4, "GLD": 0.2}
        r = mix(current, w)

    elif agent_id == "defensive":
        w = {"AGG": 0.45, "TLT": 0.35, "GLD": 0.15, "SPY": 0.05}
        r = mix(current, w)

    else:
        r = 0.0

    return r, drifted, drift_reason


class MetaFinanceExecutor:
    """Maps weekly agent outcomes to structural success/failure for kernel governance."""

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

        agent_return = ctx.agent_returns[agent.id]
        bench_return = ctx.benchmark_return
        delta = agent_return - bench_return

        if self.last_seen_week.get(agent.id) != week:
            self.delta_hist.setdefault(agent.id, []).append(delta)
            self.agent_hist.setdefault(agent.id, []).append(agent_return)
            self.bench_hist.setdefault(agent.id, []).append(bench_return)
            self.last_seen_week[agent.id] = week

        metrics = structural_metrics(
            self.delta_hist.get(agent.id, []),
            self.agent_hist.get(agent.id, []),
            self.bench_hist.get(agent.id, []),
        )

        if metrics["count"] < WINDOW:
            success = True
            signal_class = "warmup"
        else:
            structural_failure = (
                (metrics["alpha_8w"] <= -0.01 and metrics["dd_ratio"] >= 1.35)
                or metrics["min_delta_8w"] <= -0.04
            )
            if structural_failure:
                success = False
                signal_class = "failure"
            elif metrics["alpha_8w"] >= 0.0:
                success = True
                signal_class = "success"
            else:
                success = True
                signal_class = "neutral"

        dollar_impact = delta * ctx.portfolio_value_before

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.001,
            metadata={
                "weekly_return": round(agent_return, 6),
                "benchmark_return": round(bench_return, 6),
                "delta": round(delta, 6),
                "dollar_impact": round(dollar_impact, 2),
                "alpha_8w": round(metrics["alpha_8w"], 6),
                "tracking_error_8w": round(metrics["tracking_error_8w"], 6),
                "dd_agent_8w": round(metrics["dd_agent_8w"], 6),
                "dd_bench_8w": round(metrics["dd_bench_8w"], 6),
                "dd_ratio": round(metrics["dd_ratio"], 6),
                "min_delta_8w": round(metrics["min_delta_8w"], 6),
                "signal_class": signal_class,
                "regime": ctx.regime,
                "week": week,
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
    benchmark_return = float(week_data["benchmark_return"])

    urgency = 0.78 if regime == "stress" else 0.60
    tasks: List[Task] = []

    for aid in AGENTS:
        delta = agent_returns[aid] - benchmark_return
        m = structural_metrics(
            delta_hist.get(aid, []) + [delta],
            agent_hist.get(aid, []) + [agent_returns[aid]],
            bench_hist.get(aid, []) + [benchmark_return],
        )
        alpha = m["alpha_8w"]
        risk = clamp(0.08 + 10.0 * max(0.0, -alpha), 0.05, 0.35)
        impact = clamp(0.30 + 60.0 * abs(alpha), 0.10, 1.00)

        tasks.append(
            Task(
                id=f"META_{week:03d}_{aid}",
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
            raw[aid] = max(0.0, agents[aid].trust_score) ** 0.5

    total = sum(raw.values())
    if total <= 0:
        return {aid: 0.0 for aid in AGENTS}
    return {aid: raw[aid] / total for aid in AGENTS}


def run_meta_simulation() -> dict:
    if not os.path.exists(MARKET_DATA_PATH):
        raise RuntimeError("market_data.json missing. Run: python3 data/fetch_market_data.py")

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks = market_data["weeks"]
    if not weeks:
        raise RuntimeError("No weekly data in market_data.json")

    random.seed(2024)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    state = PersistentStateManager(db_path=DB_PATH)

    try:
        registry = AgentRegistry(state)
        for aid in AGENTS:
            registry.register_agent(
                agent_id=aid,
                capabilities=["signal_generation", "allocation"],
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
        loop.mutation_engine.mutation_rate = 0.003
        loop.mutation_engine.target_success_rate = 0.70
        loop.trust_engine.MAX_REDEMPTION_CYCLES = 200

        executor = MetaFinanceExecutor()

        # precompute SPY vol threshold for deterministic drift injection B
        hist = build_return_history(weeks)
        spy_vol4_series = [stdev_last(hist["SPY"][:i], 4) for i in range(1, len(weeks) + 1)]
        sorted_vol = sorted(spy_vol4_series)
        spy_vol_threshold = sorted_vol[int(0.75 * (len(sorted_vol) - 1))] if sorted_vol else 0.02

        governed_value = float(STARTING_PORTFOLIO)
        ungoverned_value = float(STARTING_PORTFOLIO)
        benchmark_value = float(STARTING_PORTFOLIO)

        peak_gov = governed_value
        peak_ung = ungoverned_value
        peak_bm = benchmark_value
        max_dd_gov = 0.0
        max_dd_ung = 0.0
        max_dd_bm = 0.0

        timeline: List[dict] = []
        all_events: List[dict] = []
        mutation_events: List[dict] = []
        drift_events_detected = 0

        delta_hist: Dict[str, List[float]] = {aid: [] for aid in AGENTS}
        agent_hist: Dict[str, List[float]] = {aid: [] for aid in AGENTS}
        bench_hist: Dict[str, List[float]] = {aid: [] for aid in AGENTS}
        cumulative_returns: Dict[str, float] = {aid: 0.0 for aid in AGENTS}
        weeks_suppressed: Dict[str, int] = {aid: 0 for aid in AGENTS}

        previous_status = {aid: "active" for aid in AGENTS}
        previous_mutation = {
            "trust_threshold": INITIAL_TRUST_THRESHOLD,
            "suppression_threshold": INITIAL_SUPPRESSION_THRESHOLD,
            "drift_delta": INITIAL_DRIFT_DELTA,
        }

        sample_finance_payload = None

        print("\n" + "=" * 84)
        print("  GOVERNED VS UNGOVERNED AUTONOMOUS FINANCE")
        print(f"  {len(weeks)} weeks | {len(AGENTS)} sleeves | benchmark: {BENCHMARK_LABEL}")
        print("  Kernel: unchanged Syntropiq governance")
        print("=" * 84)

        for i, w in enumerate(weeks):
            week = int(w["week"])
            date = w["date"]
            regime = w.get("regime", "bull")
            benchmark_return = float(w["benchmark_return"])

            week_events: List[dict] = []

            if week > 1 and regime == "stress" and weeks[week - 2].get("regime", "bull") != "stress":
                week_events.append(
                    {
                        "type": "regime_shift",
                        "color": "purple",
                        "text": f"[WEEK {week:02d}] REGIME SHIFT — Stress phase begins",
                    }
                )

            # deterministic strategy returns + drift flags
            agent_returns: Dict[str, float] = {}
            drift_flags: Dict[str, dict] = {}
            for aid in AGENTS:
                ret, drifted, reason = compute_agent_week_return(aid, i, w, hist, spy_vol_threshold)
                agent_returns[aid] = ret
                drift_flags[aid] = {"active": drifted, "reason": reason}
                if drifted:
                    drift_events_detected += 1

            # UNGOVERNED: equal-weight always
            ungoverned_return = sum(agent_returns.values()) / len(AGENTS)

            executor.set_week_context(
                WeekContext(
                    week=week,
                    date=date,
                    regime=regime,
                    benchmark_return=benchmark_return,
                    portfolio_value_before=governed_value,
                    agent_returns=agent_returns,
                )
            )

            tasks = build_tasks_for_week(w, agent_returns, delta_hist, agent_hist, bench_hist)

            agents = registry.get_agents_dict()
            trust_before = {aid: agents[aid].trust_score for aid in AGENTS}

            freeze_to_benchmark = False
            try:
                result = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"META_{week:03d}",
                )
            except ValueError as e:
                if "Total of weights must be greater than zero" not in str(e):
                    raise
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] ROUTING FREEZE — no eligible sleeves; capital held in benchmark",
                    }
                )
                freeze_to_benchmark = True
                result = {
                    "run_id": f"META_{week:03d}_freeze",
                    "results": [],
                    "trust_updates": {},
                    "mutation": previous_mutation,
                    "statistics": {"tasks_executed": 0, "successes": 0, "failures": 0, "avg_latency": 0.0},
                }

            registry.sync_trust_scores()
            agents = registry.get_agents_dict()

            status_map = {aid: agent_status_from_kernel(loop, agents[aid]) for aid in AGENTS}
            weights = authority_weights_from_trust(agents, status_map)

            if freeze_to_benchmark:
                governed_return = benchmark_return
                weights = {aid: 0.0 for aid in AGENTS}
            else:
                governed_return = sum(weights[aid] * agent_returns[aid] for aid in AGENTS)

            # events from trust updates and lifecycle transitions
            for aid, new_trust in result.get("trust_updates", {}).items():
                old = trust_before.get(aid, new_trust)
                dt = new_trust - old
                rel = agent_returns[aid] - benchmark_return
                if dt > 0:
                    week_events.append(
                        {
                            "type": "trust_increase",
                            "color": "blue",
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} delta {rel:+.2%} — trust ↑ {old:.2f} → {new_trust:.2f}"
                            ),
                        }
                    )
                elif dt < 0:
                    week_events.append(
                        {
                            "type": "trust_decrease",
                            "color": "amber",
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} delta {rel:+.2%} — trust ↓ {old:.2f} → {new_trust:.2f}"
                            ),
                        }
                    )

            for aid in AGENTS:
                prev = previous_status[aid]
                curr = status_map[aid]
                if curr == "suppressed":
                    weeks_suppressed[aid] += 1
                if prev != curr:
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
                    elif prev == "suppressed" and curr in {"active", "probation"}:
                        week_events.append(
                            {
                                "type": "redeemed",
                                "color": "green",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} REDEEMED to {curr.upper()}",
                            }
                        )

            mutation = result.get("mutation", previous_mutation)
            if abs(mutation["suppression_threshold"] - previous_mutation["suppression_threshold"]) > 1e-9:
                mutation_events.append(
                    {
                        "week": week,
                        "old_threshold": round(previous_mutation["suppression_threshold"], 3),
                        "new_threshold": round(mutation["suppression_threshold"], 3),
                    }
                )
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

            # update portfolio values
            governed_value *= 1.0 + governed_return
            ungoverned_value *= 1.0 + ungoverned_return
            benchmark_value *= 1.0 + benchmark_return

            peak_gov = max(peak_gov, governed_value)
            peak_ung = max(peak_ung, ungoverned_value)
            peak_bm = max(peak_bm, benchmark_value)
            max_dd_gov = min(max_dd_gov, (governed_value - peak_gov) / peak_gov)
            max_dd_ung = min(max_dd_ung, (ungoverned_value - peak_ung) / peak_ung)
            max_dd_bm = min(max_dd_bm, (benchmark_value - peak_bm) / peak_bm)

            for aid in AGENTS:
                delta = agent_returns[aid] - benchmark_return
                delta_hist[aid].append(delta)
                agent_hist[aid].append(agent_returns[aid])
                bench_hist[aid].append(benchmark_return)
                cumulative_returns[aid] += agent_returns[aid]

            if week == 1:
                ex = AGENTS.keys().__iter__().__next__()
                ex_delta = agent_returns[ex] - benchmark_return
                sample_finance_payload = {
                    "task": {
                        "id": f"META_{week:03d}_{ex}",
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
                        "task_id": f"META_{week:03d}_{ex}",
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

            timeline_week = {
                "week": week,
                "date": date,
                "regime": regime,
                "agents": {},
                "governed_portfolio_value": round(governed_value, 0),
                "ungoverned_portfolio_value": round(ungoverned_value, 0),
                "benchmark_value": round(benchmark_value, 0),
                "governed_return": round(governed_return, 6),
                "ungoverned_return": round(ungoverned_return, 6),
                "benchmark_return": round(benchmark_return, 6),
                "outperformance_dollar_governed_vs_bm": round(governed_value - benchmark_value, 0),
                "outperformance_dollar_ungov_vs_bm": round(ungoverned_value - benchmark_value, 0),
                "events": week_events,
                "drift_flags": drift_flags,
                # compatibility fields for existing replay consumers
                "portfolio_value": round(governed_value, 0),
                "outperformance_dollar": round(governed_value - benchmark_value, 0),
                "outperformance_pct": round((governed_value - benchmark_value) / STARTING_PORTFOLIO * 100, 2),
                "max_drawdown_portfolio": round(max_dd_gov, 4),
                "max_drawdown_benchmark": round(max_dd_bm, 4),
            }

            for aid in AGENTS:
                timeline_week["agents"][aid] = {
                    "trust": round(agents[aid].trust_score, 4),
                    "authority_weight": round(weights[aid], 4),
                    "status": status_map[aid],
                    "weekly_return": round(agent_returns[aid], 6),
                    "benchmark_delta": round(agent_returns[aid] - benchmark_return, 6),
                    "cumulative_return": round(cumulative_returns[aid], 6),
                }

            timeline.append(timeline_week)
            all_events.extend(week_events)
            previous_status = status_map

            if week % 10 == 0 or week == 1:
                print(
                    f"  Week {week:3d} [{regime:6s}] GOV ${governed_value:>11,.0f} | "
                    f"UNG ${ungoverned_value:>11,.0f} | BM ${benchmark_value:>11,.0f}"
                )

        governed_outperf = governed_value - benchmark_value
        ungoverned_outperf = ungoverned_value - benchmark_value

        summary = {
            "final_governed_value": round(governed_value, 0),
            "final_ungoverned_value": round(ungoverned_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "total_outperformance_dollar_governed_vs_bm": round(governed_outperf, 0),
            "total_outperformance_pct_governed_vs_bm": round((governed_value / benchmark_value - 1) * 100, 2),
            "total_outperformance_dollar_ungov_vs_bm": round(ungoverned_outperf, 0),
            "total_outperformance_pct_ungov_vs_bm": round((ungoverned_value / benchmark_value - 1) * 100, 2),
            "max_drawdown_governed": round(max_dd_gov, 4),
            "max_drawdown_ungoverned": round(max_dd_ung, 4),
            "max_drawdown_benchmark": round(max_dd_bm, 4),
            "total_governance_events": len(all_events),
            "drift_events_detected": drift_events_detected,
            "mutation_events": mutation_events,
            "weeks_suppressed_by_agent": weeks_suppressed,
            "total_weeks": len(timeline),
            "starting_portfolio": STARTING_PORTFOLIO,
            "benchmark": BENCHMARK_LABEL,
            "data_source": "yfinance (real)",
            "sleeves": list(AGENTS.keys()),
            "payload_comparison": {
                "finance": sample_finance_payload,
                "lending": LENDING_PAYLOAD_REFERENCE,
            },
            # compatibility fields
            "final_portfolio_value": round(governed_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "total_outperformance_dollar": round(governed_outperf, 0),
            "total_outperformance_pct": round((governed_value / benchmark_value - 1) * 100, 2),
        }

        for aid, count in weeks_suppressed.items():
            summary[f"weeks_{aid}_suppressed"] = count

        output = {"summary": summary, "timeline": timeline}

        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        with open(UNGOV_OUTPUT_PATH, "w") as f:
            json.dump(
                {
                    "summary": {
                        "final_ungoverned_value": round(ungoverned_value, 0),
                        "final_benchmark_value": round(benchmark_value, 0),
                        "total_outperformance_dollar_ungov_vs_bm": round(ungoverned_outperf, 0),
                        "total_outperformance_pct_ungov_vs_bm": round((ungoverned_value / benchmark_value - 1) * 100, 2),
                        "max_drawdown_ungoverned": round(max_dd_ung, 4),
                        "max_drawdown_benchmark": round(max_dd_bm, 4),
                    },
                    "timeline": [
                        {
                            "week": t["week"],
                            "date": t["date"],
                            "regime": t["regime"],
                            "ungoverned_portfolio_value": t["ungoverned_portfolio_value"],
                            "benchmark_value": t["benchmark_value"],
                            "ungoverned_return": t["ungoverned_return"],
                            "benchmark_return": t["benchmark_return"],
                        }
                        for t in timeline
                    ],
                },
                f,
                indent=2,
            )

        print("\n" + "=" * 84)
        print("  META SIMULATION COMPLETE")
        print("=" * 84)
        print(f"  Governed:   ${governed_value:,.0f}")
        print(f"  Ungoverned: ${ungoverned_value:,.0f}")
        print(f"  Benchmark:  ${benchmark_value:,.0f}")
        print(f"  Events:     {len(all_events)}")
        print(f"  Drift flags detected: {drift_events_detected}")
        print(f"  Output: {OUTPUT_PATH}")
        print(f"  Baseline: {UNGOV_OUTPUT_PATH}")

        return output

    finally:
        state.close()


if __name__ == "__main__":
    run_meta_simulation()
