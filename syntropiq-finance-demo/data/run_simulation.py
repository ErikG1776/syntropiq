#!/usr/bin/env python3
"""
Syntropiq Finance Demo (Category C)
Enterprise Governance for Autonomous Capital Engines

Kernel remains unchanged. This file is a thin finance domain wrapper:
- real historical weekly market data in market_data.json
- 10 autonomous sleeves (fixed allocation engines)
- governance and trust dynamics from real Syntropiq kernel only
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
from dataclasses import dataclass
from typing import Dict, List

# add repo root for Syntropiq imports when run from syntropiq-finance-demo/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")
DB_PATH = os.path.join(DATA_DIR, "finance_demo.db")

STARTING_PORTFOLIO = 10_000_000
INITIAL_TRUST = 0.75

# Kernel initialization only; no custom trust/suppression logic.
INITIAL_TRUST_THRESHOLD = 0.70
INITIAL_SUPPRESSION_THRESHOLD = 0.75
INITIAL_DRIFT_DELTA = 0.10
ROUTING_MODE = "competitive"

WINDOW = 8

TICKERS = ["QQQ", "SPY", "TLT", "AGG", "XLF", "GLD", "USO", "EEM", "IWM", "HYG"]

AGENTS: Dict[str, Dict] = {
    "growth": {
        "label": "Growth Sleeve",
        "allocation": {"QQQ": 0.55, "SPY": 0.25, "IWM": 0.10, "XLF": 0.10},
    },
    "risk": {
        "label": "Defensive Sleeve",
        "allocation": {"AGG": 0.45, "TLT": 0.40, "GLD": 0.10, "SPY": 0.05},
    },
    "macro": {
        "label": "Macro Mix Sleeve",
        "allocation": {
            "QQQ": 0.12,
            "SPY": 0.18,
            "TLT": 0.18,
            "AGG": 0.18,
            "XLF": 0.08,
            "GLD": 0.10,
            "USO": 0.06,
            "EEM": 0.06,
            "IWM": 0.04,
        },
    },
    "value": {
        "label": "Value Sleeve",
        "allocation": {"SPY": 0.35, "XLF": 0.35, "IWM": 0.20, "AGG": 0.10},
    },
    "credit": {
        "label": "Credit Sleeve",
        "allocation": {"HYG": 0.55, "AGG": 0.35, "SPY": 0.10},
    },
    "commodities": {
        "label": "Commodities Sleeve",
        "allocation": {"USO": 0.50, "GLD": 0.35, "SPY": 0.10, "AGG": 0.05},
    },
    "em": {
        "label": "EM Sleeve",
        "allocation": {"EEM": 0.70, "SPY": 0.15, "AGG": 0.15},
    },
    "smallcap": {
        "label": "SmallCap Sleeve",
        "allocation": {"IWM": 0.70, "SPY": 0.20, "AGG": 0.10},
    },
    "balanced": {
        "label": "Balanced Sleeve",
        "allocation": {"SPY": 0.35, "AGG": 0.35, "QQQ": 0.20, "TLT": 0.10},
    },
    "trend": {
        "label": "Trend Sleeve",
        "allocation": {
            "SPY": 0.25,
            "QQQ": 0.20,
            "AGG": 0.20,
            "TLT": 0.15,
            "GLD": 0.10,
            "USO": 0.10,
        },
    },
}

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


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def compute_agent_return(agent_id: str, week_data: dict) -> float:
    returns = week_data["tickers"]
    alloc = AGENTS[agent_id]["allocation"]

    value = 0.0
    for ticker, weight in alloc.items():
        ticker_ret = returns.get(ticker, {}).get("weekly_return", 0.0)
        value += weight * ticker_ret

    return value


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
        if dd > max_dd:
            max_dd = dd
    return max_dd


def rolling_signal_metrics(deltas: List[float], agent_returns: List[float], bench_returns: List[float]) -> dict:
    d = deltas
    a = agent_returns
    b = bench_returns

    if not d or not a or not b:
        return {
            "alpha_8w": 0.0,
            "te_8w": 0.0,
            "dd_agent_8w": 0.0,
            "dd_bench_8w": 0.0,
            "dd_ratio": 0.0,
            "min_delta_8w": 0.0,
            "count": 0,
        }

    alpha_8w = statistics.fmean(d)
    te_8w = statistics.pstdev(d) if len(d) > 1 else 0.0
    dd_agent_8w = max_drawdown_from_returns(a)
    dd_bench_8w = max_drawdown_from_returns(b)
    dd_ratio = dd_agent_8w / max(dd_bench_8w, 1e-9)
    min_delta_8w = min(d)

    return {
        "alpha_8w": alpha_8w,
        "te_8w": te_8w,
        "dd_agent_8w": dd_agent_8w,
        "dd_bench_8w": dd_bench_8w,
        "dd_ratio": dd_ratio,
        "min_delta_8w": min_delta_8w,
        "count": len(d),
    }


@dataclass
class WeekContext:
    week: int
    date: str
    regime: str
    benchmark_return: float
    portfolio_value_before: float
    agent_returns: Dict[str, float]


class FinanceExecutor:
    """Finance domain execution with structural 8-week misalignment signal."""

    def __init__(self):
        self.context_by_week: Dict[int, WeekContext] = {}
        self.delta_history: Dict[str, List[float]] = {}
        self.agent_return_history: Dict[str, List[float]] = {}
        self.benchmark_return_history: Dict[str, List[float]] = {}
        self._last_seen_week_by_agent: Dict[str, int] = {}

    def set_week_context(self, ctx: WeekContext):
        self.context_by_week[ctx.week] = ctx

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        week = int(task.metadata["week"])
        ctx = self.context_by_week[week]

        agent_return = ctx.agent_returns[agent.id]
        benchmark_return = ctx.benchmark_return
        delta = agent_return - benchmark_return

        if self._last_seen_week_by_agent.get(agent.id) != week:
            self.delta_history.setdefault(agent.id, []).append(delta)
            self.agent_return_history.setdefault(agent.id, []).append(agent_return)
            self.benchmark_return_history.setdefault(agent.id, []).append(benchmark_return)
            self._last_seen_week_by_agent[agent.id] = week

        window = 4 if ctx.regime == "stress" else 8
        metrics = rolling_signal_metrics(
            self.delta_history.get(agent.id, [])[-window:],
            self.agent_return_history.get(agent.id, [])[-window:],
            self.benchmark_return_history.get(agent.id, [])[-window:]
        )

        if metrics["count"] < window:
            success = True
            outcome_class = "warmup"
        else:
            if ctx.regime == "stress":
                structural_failure = (
                    metrics["alpha_8w"] <= -0.012
                    and metrics["dd_agent_8w"] > metrics["dd_bench_8w"]
                    and metrics["dd_ratio"] >= 1.5
                )
            else:
                structural_failure = (
                    metrics["alpha_8w"] <= -0.012
                    or metrics["min_delta_8w"] <= -0.045
                )

            structural_success = (
                metrics["alpha_8w"] >= 0.001
                and metrics["dd_ratio"] <= 1.3
            )

            if structural_failure:
                success = False
                outcome_class = "failure"
            elif structural_success:
                success = True
                outcome_class = "success"
            else:
                success = True
                outcome_class = "neutral"

        dollar_impact = delta * ctx.portfolio_value_before

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.001,
            metadata={
                "decision": "OUTPERFORMED" if success else "UNDERPERFORMED",
                "outcome": "ALPHA_GENERATED" if success else "STRUCTURAL_MISALIGNMENT",
                "signal_class": outcome_class,
                "weekly_return": round(agent_return, 6),
                "benchmark_return": round(benchmark_return, 6),
                "delta": round(delta, 6),
                "dollar_impact": round(dollar_impact, 2),
                "alpha_8w": round(metrics["alpha_8w"], 6),
                "te_8w": round(metrics["te_8w"], 6),
                "dd_agent_8w": round(metrics["dd_agent_8w"], 6),
                "dd_bench_8w": round(metrics["dd_bench_8w"], 6),
                "dd_ratio": round(metrics["dd_ratio"], 6),
                "min_delta_8w": round(metrics["min_delta_8w"], 6),
                "regime": ctx.regime,
                "week": ctx.week,
                "date": ctx.date,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in AGENTS


def build_tasks_for_week(
    week_data: dict,
    agent_returns: Dict[str, float],
    delta_history: Dict[str, List[float]],
    agent_return_history: Dict[str, List[float]],
    bench_return_history: Dict[str, List[float]],
) -> List[Task]:
    week = int(week_data["week"])
    date = week_data["date"]
    regime = week_data.get("regime", "bull")
    benchmark_return = float(week_data["benchmark_return"])

    tasks: List[Task] = []
    urgency = 0.78 if regime == "stress" else 0.60

    # One task per sleeve, every week.
    for aid in AGENTS:
        delta = agent_returns[aid] - benchmark_return

        preview_deltas = delta_history.get(aid, []) + [delta]
        preview_agent_returns = agent_return_history.get(aid, []) + [agent_returns[aid]]
        preview_bench_returns = bench_return_history.get(aid, []) + [benchmark_return]
        metrics = rolling_signal_metrics(
            preview_deltas[-WINDOW:],
            preview_agent_returns[-WINDOW:],
            preview_bench_returns[-WINDOW:],
        )

        alpha_8w = metrics["alpha_8w"]
        risk = clamp(0.08 + 10.0 * max(0.0, -alpha_8w), 0.05, 0.35)
        impact = clamp(0.30 + 60.0 * abs(alpha_8w), 0.10, 1.00)

        tasks.append(
            Task(
                id=f"ALLOC_{week:03d}_{aid}",
                impact=round(impact, 4),
                urgency=urgency,
                risk=round(risk, 4),
                metadata={
                    "week": week,
                    "date": date,
                    "regime": regime,
                    "candidate_agent": aid,
                    "delta": round(delta, 6),
                    "alpha_8w": round(metrics["alpha_8w"], 6),
                    "te_8w": round(metrics["te_8w"], 6),
                    "dd_agent_8w": round(metrics["dd_agent_8w"], 6),
                    "dd_bench_8w": round(metrics["dd_bench_8w"], 6),
                    "dd_ratio": round(metrics["dd_ratio"], 6),
                    "min_delta_8w": round(metrics["min_delta_8w"], 6),
                    "benchmark_return": round(benchmark_return, 6),
                    "allocation": AGENTS[aid]["allocation"],
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


def run_simulation():
    if not os.path.exists(MARKET_DATA_PATH):
        raise RuntimeError("market_data.json missing. Run: python3 data/fetch_market_data.py")

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks_data = market_data["weeks"]
    if not weeks_data:
        raise RuntimeError("No weekly market data rows found")

    # deterministic routing behavior for competitive mode
    random.seed(2024)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    state = PersistentStateManager(db_path=DB_PATH)

    try:
        registry = AgentRegistry(state)
        for aid in AGENTS:
            registry.register_agent(
                agent_id=aid,
                capabilities=["allocation"],
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

        # kernel settings only (no logic replacement)
        loop.mutation_engine.mutation_rate = 0.003
        loop.mutation_engine.target_success_rate = 0.70
        loop.trust_engine.MAX_REDEMPTION_CYCLES = 200

        executor = FinanceExecutor()

        portfolio_value = float(STARTING_PORTFOLIO)
        benchmark_value = float(STARTING_PORTFOLIO)
        peak_portfolio = portfolio_value
        peak_benchmark = benchmark_value
        max_drawdown_portfolio = 0.0
        max_drawdown_benchmark = 0.0

        timeline: List[dict] = []
        all_events: List[dict] = []
        mutation_events: List[dict] = []

        cumulative_returns = {aid: 0.0 for aid in AGENTS}
        weeks_suppressed = {aid: 0 for aid in AGENTS}
        weeks_led = {aid: 0 for aid in AGENTS}

        # Histories for task shaping (one value per sleeve per week)
        task_delta_history: Dict[str, List[float]] = {aid: [] for aid in AGENTS}
        task_agent_return_history: Dict[str, List[float]] = {aid: [] for aid in AGENTS}
        task_bench_return_history: Dict[str, List[float]] = {aid: [] for aid in AGENTS}

        previous_status = {aid: "active" for aid in AGENTS}
        previous_mutation = {
            "trust_threshold": INITIAL_TRUST_THRESHOLD,
            "suppression_threshold": INITIAL_SUPPRESSION_THRESHOLD,
            "drift_delta": INITIAL_DRIFT_DELTA,
        }

        sample_finance_payload = None

        print("\n" + "=" * 78)
        print("  ENTERPRISE GOVERNANCE FOR AUTONOMOUS CAPITAL ENGINES")
        print(f"  {len(weeks_data)} weeks | 10 sleeves | real market data")
        print("  Governance: Syntropiq kernel unchanged")
        print("=" * 78)

        for w in weeks_data:
            week = int(w["week"])
            date = w["date"]
            regime = w.get("regime", "bull")
            benchmark_return = float(w["benchmark_return"])

            week_events: List[dict] = []

            # first stress transition marker
            if week > 1 and regime == "stress" and weeks_data[week - 2].get("regime", "bull") != "stress":
                week_events.append(
                    {
                        "type": "regime_shift",
                        "color": "purple",
                        "text": f"[WEEK {week:02d}] REGIME SHIFT DETECTED — Stress phase begins",
                    }
                )

            agent_returns = {aid: compute_agent_return(aid, w) for aid in AGENTS}

            executor.set_week_context(
                WeekContext(
                    week=week,
                    date=date,
                    regime=regime,
                    benchmark_return=benchmark_return,
                    portfolio_value_before=portfolio_value,
                    agent_returns=agent_returns,
                )
            )

            tasks = build_tasks_for_week(
                week_data=w,
                agent_returns=agent_returns,
                delta_history=task_delta_history,
                agent_return_history=task_agent_return_history,
                bench_return_history=task_bench_return_history,
            )

            agents = registry.get_agents_dict()
            trust_before = {aid: agents[aid].trust_score for aid in AGENTS}
            freeze_weights = False

            try:
                result = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"FINANCE_{week:03d}",
                )
            except ValueError as e:
                if "Total of weights must be greater than zero" not in str(e):
                    raise

                # Governance routing freeze — no eligible agents
                week_events.append(
                    {
                        "type": "routing_freeze",
                        "color": "red",
                        "text": f"[WEEK {week:02d}] ROUTING FREEZE — no eligible sleeves; capital held",
                    }
                )

                # Do NOT call execute_cycle again.
                # Instead create a no-execution result for this week.
                result = {
                    "run_id": f"FINANCE_{week:03d}_freeze",
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

                # IMPORTANT:
                # Set weights to zero so portfolio return becomes 0 for this week.
                weights = {aid: 0.0 for aid in AGENTS}
                freeze_weights = True

            registry.sync_trust_scores()
            agents = registry.get_agents_dict()

            status_map = {aid: agent_status_from_kernel(loop, agents[aid]) for aid in AGENTS}
            if not freeze_weights:
                weights = authority_weights_from_trust(agents, status_map)

            for aid, new_trust in result.get("trust_updates", {}).items():
                old = trust_before.get(aid, new_trust)
                delta_trust = new_trust - old
                rel = agent_returns[aid] - benchmark_return

                if delta_trust > 0:
                    week_events.append(
                        {
                            "type": "trust_increase",
                            "color": "blue",
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} outperformed benchmark "
                                f"{rel:+.2%} — trust ↑ {old:.2f} → {new_trust:.2f}"
                            ),
                        }
                    )
                elif delta_trust < 0:
                    magnitude = abs(delta_trust)
                    if magnitude >= 0.05:
                        t, c = "trust_decrease_severe", "red"
                    elif magnitude >= 0.03:
                        t, c = "trust_decrease_moderate", "amber"
                    else:
                        t, c = "trust_decrease", "amber"
                    week_events.append(
                        {
                            "type": t,
                            "color": c,
                            "text": (
                                f"[WEEK {week:02d}] {AGENTS[aid]['label']} underperformed benchmark "
                                f"{rel:+.2%} — trust ↓ {old:.2f} → {new_trust:.2f}"
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
                                "type": "suppression",
                                "color": "red",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} SUPPRESSED — authority set to 0",
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
                                "type": "redemption",
                                "color": "green",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} redeemed to {curr.upper()}",
                            }
                        )
                    elif curr == "active":
                        week_events.append(
                            {
                                "type": "recovery",
                                "color": "green",
                                "text": f"[WEEK {week:02d}] {AGENTS[aid]['label']} restored to ACTIVE",
                            }
                        )

            mutation = result.get("mutation", previous_mutation)
            old_sup = previous_mutation["suppression_threshold"]
            new_sup = mutation["suppression_threshold"]
            if abs(new_sup - old_sup) > 1e-9:
                week_events.append(
                    {
                        "type": "mutation",
                        "color": "purple",
                        "text": f"[WEEK {week:02d}] THRESHOLD MUTATION — suppression {old_sup:.2f} → {new_sup:.2f}",
                    }
                )
                mutation_events.append(
                    {
                        "week": week,
                        "old_threshold": round(old_sup, 3),
                        "new_threshold": round(new_sup, 3),
                    }
                )
            previous_mutation = mutation

            portfolio_return = sum(weights[aid] * agent_returns[aid] for aid in AGENTS)
            portfolio_value *= 1.0 + portfolio_return
            benchmark_value *= 1.0 + benchmark_return

            peak_portfolio = max(peak_portfolio, portfolio_value)
            peak_benchmark = max(peak_benchmark, benchmark_value)
            dd_p = (portfolio_value - peak_portfolio) / peak_portfolio
            dd_b = (benchmark_value - peak_benchmark) / peak_benchmark
            max_drawdown_portfolio = min(max_drawdown_portfolio, dd_p)
            max_drawdown_benchmark = min(max_drawdown_benchmark, dd_b)

            for aid in AGENTS:
                cumulative_returns[aid] += agent_returns[aid]

                # Update task-shaping histories once per sleeve per week.
                task_delta_history[aid].append(agent_returns[aid] - benchmark_return)
                task_agent_return_history[aid].append(agent_returns[aid])
                task_bench_return_history[aid].append(benchmark_return)

            leader = max(weights, key=weights.get)
            weeks_led[leader] += 1

            if week == 1:
                growth_ret = agent_returns["growth"]
                growth_delta = growth_ret - benchmark_return
                sample_finance_payload = {
                    "task": {
                        "id": f"ALLOC_{week:03d}_growth",
                        "impact": round(tasks[0].impact, 3),
                        "urgency": round(tasks[0].urgency, 3),
                        "risk": round(tasks[0].risk, 3),
                        "metadata": {
                            "weekly_return": round(growth_ret, 6),
                            "benchmark_delta": round(growth_delta, 6),
                            "regime": regime,
                            "allocation": AGENTS["growth"]["allocation"],
                        },
                    },
                    "result": {
                        "task_id": f"ALLOC_{week:03d}_growth",
                        "agent_id": "growth",
                        "success": growth_ret >= benchmark_return,
                        "metadata": {
                            "decision": "OUTPERFORMED" if growth_ret >= benchmark_return else "UNDERPERFORMED",
                            "outcome": "ALPHA_GENERATED" if growth_ret >= benchmark_return else "BENCHMARK_MISS",
                            "benchmark_delta": round(growth_delta, 6),
                            "authority_weight": round(weights["growth"], 4),
                        },
                    },
                    "governance_response": {
                        "trust_update": {"growth": round(agents["growth"].trust_score, 3)},
                        "status": status_map["growth"],
                        "mutation": {"suppression_threshold": round(new_sup, 3)},
                    },
                }

            week_record = {
                "week": week,
                "date": date,
                "regime": regime,
                "agents": {},
                "portfolio_value": round(portfolio_value, 0),
                "benchmark_value": round(benchmark_value, 0),
                "portfolio_return": round(portfolio_return, 6),
                "benchmark_return": round(benchmark_return, 6),
                "outperformance_dollar": round(portfolio_value - benchmark_value, 0),
                "outperformance_pct": round((portfolio_value - benchmark_value) / STARTING_PORTFOLIO * 100, 2),
                "events": week_events,
                "regime_shift": week_events and any(e["type"] == "regime_shift" for e in week_events),
                "suppression_floor": round(new_sup, 3),
                "max_drawdown_portfolio": round(max_drawdown_portfolio, 4),
                "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
            }

            for aid in AGENTS:
                week_record["agents"][aid] = {
                    "trust": round(agents[aid].trust_score, 4),
                    "authority_weight": round(weights[aid], 4),
                    "status": status_map[aid],
                    "weekly_return": round(agent_returns[aid], 6),
                    "benchmark_delta": round(agent_returns[aid] - benchmark_return, 6),
                    "cumulative_return": round(cumulative_returns[aid], 6),
                    "allocation": AGENTS[aid]["allocation"],
                }

            timeline.append(week_record)
            all_events.extend(week_events)
            previous_status = status_map

            if week % 10 == 0 or week == 1:
                status_snapshot = " | ".join(
                    f"{aid}:{agents[aid].trust_score:.2f}({status_map[aid][:3].upper()})"
                    for aid in ["growth", "risk", "macro"]
                )
                print(
                    f"  Week {week:3d} [{regime:6s}] ${portfolio_value:>12,.0f} "
                    f"vs BM: ${portfolio_value - benchmark_value:>+10,.0f} | {status_snapshot}"
                )

        # summary
        bull_weeks = [w for w in timeline if w["regime"] == "bull"]
        stress_weeks = [w for w in timeline if w["regime"] == "stress"]

        first_stress = next((w["week"] for w in timeline if w["regime"] == "stress"), None)

        risk_led_weeks = [
            w["week"]
            for w in timeline
            if w["agents"]["risk"]["authority_weight"]
            == max(w["agents"][aid]["authority_weight"] for aid in AGENTS)
        ]

        suppression_outperformance = sum(
            (w["portfolio_return"] - w["benchmark_return"])
            for w in timeline
            if w["agents"]["growth"]["status"] == "suppressed"
        )
        total_outperformance = portfolio_value - benchmark_value

        suppression_attr = round(suppression_outperformance * STARTING_PORTFOLIO, 0)
        elevation_attr = round(
            sum(
                max(0.0, w["agents"]["risk"]["authority_weight"] - (1.0 / len(AGENTS)))
                * w["agents"]["risk"]["weekly_return"]
                for w in stress_weeks
            )
            * STARTING_PORTFOLIO,
            0,
        )
        mutation_attr = round(total_outperformance - suppression_attr - elevation_attr, 0)

        regime_perf = {}
        for aid in AGENTS:
            bull_ret = sum(w["agents"][aid]["weekly_return"] for w in bull_weeks)
            stress_ret = sum(w["agents"][aid]["weekly_return"] for w in stress_weeks)
            active_weeks = sum(1 for w in timeline if w["agents"][aid]["status"] == "active")
            regime_perf[aid] = {
                "bull_return": round(bull_ret * 100, 2),
                "stress_return": round(stress_ret * 100, 2),
                "full_return": round((bull_ret + stress_ret) * 100, 2),
                "weeks_active": active_weeks,
            }

        bm_bull = sum(w["benchmark_return"] for w in bull_weeks)
        bm_stress = sum(w["benchmark_return"] for w in stress_weeks)
        regime_perf["benchmark"] = {
            "bull_return": round(bm_bull * 100, 2),
            "stress_return": round(bm_stress * 100, 2),
            "full_return": round((bm_bull + bm_stress) * 100, 2),
            "weeks_active": len(timeline),
        }

        dd_reduction = 0.0
        if max_drawdown_benchmark != 0:
            dd_reduction = round((1 - max_drawdown_portfolio / max_drawdown_benchmark) * 100, 0)

        mutation_history = state.get_mutation_history(limit=500)

        summary = {
            "final_portfolio_value": round(portfolio_value, 0),
            "final_benchmark_value": round(benchmark_value, 0),
            "total_outperformance_dollar": round(total_outperformance, 0),
            "total_outperformance_pct": round((portfolio_value / benchmark_value - 1) * 100, 2),
            "max_drawdown_governed": round(max_drawdown_portfolio, 4),
            "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
            "drawdown_reduction_pct": dd_reduction,
            "weeks_growth_suppressed": weeks_suppressed.get("growth", 0),
            "weeks_risk_led": len(risk_led_weeks),
            "total_governance_events": len(all_events),
            "regime_shift_week": first_stress,
            "total_weeks": len(timeline),
            "starting_portfolio": STARTING_PORTFOLIO,
            "agent_regime_performance": regime_perf,
            "attribution": {
                "suppression_of_growth": suppression_attr,
                "elevation_of_risk": elevation_attr,
                "threshold_mutation": mutation_attr,
            },
            "mutation_events": mutation_events,
            "payload_comparison": {
                "finance": sample_finance_payload,
                "lending": LENDING_PAYLOAD_REFERENCE,
            },
            "governance_parameters": {
                "starting_trust": INITIAL_TRUST,
                "routing_mode": ROUTING_MODE,
                "initial_trust_threshold": INITIAL_TRUST_THRESHOLD,
                "initial_suppression_threshold": INITIAL_SUPPRESSION_THRESHOLD,
                "initial_drift_delta": INITIAL_DRIFT_DELTA,
                "kernel_mutation_events_persisted": len(mutation_history),
                "kernel_db_path": DB_PATH,
                "weeks_suppressed_by_agent": weeks_suppressed,
            },
            "data_source": "yfinance (real)",
            "benchmark": "60% SPY / 40% AGG",
            "sleeves": list(AGENTS.keys()),
        }

        # also expose per-agent suppression counts at summary top-level (UI-safe additive keys)
        for aid, count in weeks_suppressed.items():
            summary[f"weeks_{aid}_suppressed"] = count

        output = {"summary": summary, "timeline": timeline}

        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        print("\n" + "=" * 78)
        print("  SIMULATION COMPLETE")
        print("=" * 78)
        print(f"\n  Portfolio:      ${portfolio_value:>14,.0f}")
        print(f"  Benchmark:      ${benchmark_value:>14,.0f}")
        print(
            f"  Outperformance: ${total_outperformance:>+14,.0f} "
            f"({summary['total_outperformance_pct']:+.2f}%)"
        )
        print("\n  Governance:")
        print(f"    Events:       {len(all_events)}")
        print(f"    Mutations:    {len(mutation_events)}")
        print(f"    DB mutations: {len(mutation_history)}")
        all_suppressed_weeks = sum(
            1
            for w in timeline
            if all(w["agents"][aid]["status"] == "suppressed" for aid in AGENTS)
        )
        suppression_event_count = sum(1 for e in all_events if e.get("type") == "suppression")
        top_3_leaders = sorted(weeks_led.items(), key=lambda kv: kv[1], reverse=True)[:3]
        print("\n  Validation:")
        print(f"    Final vs BM:  ${portfolio_value:,.0f} vs ${benchmark_value:,.0f}")
        print(
            "    Max DD:       "
            f"{max_drawdown_portfolio:.2%} governed vs {max_drawdown_benchmark:.2%} benchmark"
        )
        print(f"    All-suppressed weeks: {all_suppressed_weeks}")
        print(f"    Suppression events:   {suppression_event_count}")
        print(
            "    Top leaders:   "
            + ", ".join(f"{aid} ({weeks} weeks)" for aid, weeks in top_3_leaders)
        )
        print(f"\n  Output: {OUTPUT_PATH}")

        return output

    finally:
        state.close()


if __name__ == "__main__":
    run_simulation()
