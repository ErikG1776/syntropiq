#!/usr/bin/env python3
"""
Syntropiq Adaptive Allocation Governance Engine — Simulation Runner

Runs the full 104-week simulation using real market data and the Syntropiq
governance kernel. Precomputes all data for the React frontend.

Uses the SAME governance primitives as the fraud, lending, and readmission
demos — GovernanceLoop, TrustEngine, MutationEngine, LearningEngine.
Only the domain mapping changes (via FinanceAllocationExecutor).

Domain Mapping:
    Prior demos          -> Finance demo
    ──────────────────────────────────────────
    Loan approval        -> Capital allocation
    Default event        -> Underperformance vs benchmark
    Default severity     -> Magnitude of underperformance delta
    Recovery             -> Sustained outperformance
    Dollar loss          -> Portfolio underperformance in dollars

Architecture:
    1. Weekly market returns -> Task objects (one per agent per week)
    2. Tasks fed to GovernanceLoop.execute_cycle()
    3. FinanceAllocationExecutor maps allocation -> ExecutionResult
    4. TrustEngine applies asymmetric learning (real kernel)
    5. MutationEngine adjusts thresholds (real kernel)
    6. Suppression/redemption handled by TrustEngine (real kernel)
    7. Authority weights derived from kernel trust scores
    8. Portfolio allocation follows authority weights

Output: simulation_data.json (consumed by React frontend)

Usage:
    python data/run_simulation.py
"""

import json
import math
import os
import random
import sys

# Add parent directory to path for Syntropiq imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.core.exceptions import CircuitBreakerTriggered, NoAgentsAvailable
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from executor import FinanceAllocationExecutor, AGENT_ALLOCATIONS

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")

# ── Agent Definitions ────────────────────────────────────────────

AGENTS = {
    "growth": {
        "label": "Growth Agent",
        "allocation": AGENT_ALLOCATIONS["growth"],
        "description": "Tech-heavy allocation, outperforms in bull, degrades in stress",
    },
    "risk": {
        "label": "Risk Agent",
        "allocation": AGENT_ALLOCATIONS["risk"],
        "description": "Bond-heavy allocation, underperforms in bull, outperforms in stress",
    },
    "macro": {
        "label": "Macro Agent",
        "allocation": AGENT_ALLOCATIONS["macro"],
        "description": "Balanced allocation, moderate across regimes",
    },
}

STARTING_TRUST = 0.75
STARTING_PORTFOLIO = 10_000_000


def create_agents():
    """Create Agent objects for the governance kernel."""
    return {
        aid: Agent(
            id=aid,
            trust_score=STARTING_TRUST,
            capabilities=["allocation"],
            status="active",
        )
        for aid in AGENTS
    }


def create_week_tasks(week_data: dict, week_num: int) -> list:
    """
    Convert weekly market data into Task objects — one per agent.

    Each task represents: "Evaluate this agent's allocation against
    this week's market conditions." The risk field encodes regime
    stress (higher risk in stress regime).
    """
    regime = week_data["regime"]
    benchmark_return = week_data["benchmark_return"]

    # Extract ticker returns
    ticker_returns = {
        ticker: data["weekly_return"]
        for ticker, data in week_data["tickers"].items()
    }

    tasks = []
    for aid in AGENTS:
        # Impact: higher when market is volatile (larger absolute benchmark moves)
        impact = min(1.0, abs(benchmark_return) * 100 + 0.5)
        # Urgency: always high for weekly rebalancing
        urgency = 0.8
        # Risk: stress regime has higher risk
        risk = 0.6 if regime == "stress" else 0.3

        task = Task(
            id=f"ALLOC_{week_num:03d}_{aid}",
            impact=round(impact, 3),
            urgency=urgency,
            risk=round(risk, 3),
            metadata={
                "ticker_returns": ticker_returns,
                "benchmark_return": benchmark_return,
                "week_num": week_num,
                "regime": regime,
                "agent_target": aid,
            },
        )
        tasks.append(task)

    return tasks


def derive_authority_weights(agents: dict, trust_engine) -> dict:
    """
    Derive portfolio authority weights from kernel state.

    Reads trust scores and suppression status directly from the
    TrustEngine — no custom weight math.

    Weight rules (same as competitive routing):
    - Suppressed agents: weight = 0
    - Probation agents: weight = trust_score * 0.5
    - Active agents: weight = trust_score
    - Normalize to sum to 1.0
    """
    raw_weights = {}
    for aid, agent in agents.items():
        if aid in trust_engine.suppressed_agents:
            raw_weights[aid] = 0.0
        elif aid in trust_engine.probation_agents:
            raw_weights[aid] = agent.trust_score * 0.5
        else:
            raw_weights[aid] = agent.trust_score

    total = sum(raw_weights.values())
    if total > 0:
        return {aid: round(w / total, 4) for aid, w in raw_weights.items()}

    # All suppressed — fallback: weight by relative trust (least-bad leads)
    trust_sum = sum(max(0.01, agents[a].trust_score) for a in agents)
    return {
        aid: round(max(0.01, agents[aid].trust_score) / trust_sum, 4)
        for aid in agents
    }


def get_agent_status_from_kernel(agent_id: str, agents: dict, trust_engine) -> str:
    """Read agent status from the kernel's TrustEngine state."""
    if agent_id in trust_engine.suppressed_agents:
        return "suppressed"
    if agent_id in trust_engine.probation_agents:
        return "probation"
    return "active"


def run_simulation():
    """Run the full 104-week governance simulation using the real Syntropiq kernel."""

    # ── Load market data ──────────────────────────────────────
    if not os.path.exists(MARKET_DATA_PATH):
        print("Market data not found. Generating...")
        from fetch_market_data import generate_market_data
        generate_market_data()

    with open(MARKET_DATA_PATH, "r") as f:
        market_data = json.load(f)

    weeks_data = market_data["weeks"]
    print(f"\n{'='*78}")
    print(f"  SYNTROPIQ ADAPTIVE ALLOCATION GOVERNANCE ENGINE")
    print(f"  {len(weeks_data)}-week simulation | $10M starting portfolio")
    print(f"  Governance: Real Syntropiq Kernel (GovernanceLoop + TrustEngine + MutationEngine)")
    print(f"{'='*78}")

    # ── Initialize Syntropiq governance kernel ────────────────
    # Same pattern as lending/fraud/readmission demos
    state = PersistentStateManager(db_path=":memory:")
    loop = GovernanceLoop(
        state_manager=state,
        trust_threshold=0.55,
        suppression_threshold=0.40,
        drift_delta=0.08,
        routing_mode="competitive",
    )
    # Finance-specific tuning (same as other demos — only parameters differ)
    loop.mutation_engine.mutation_rate = 0.015
    loop.mutation_engine.target_success_rate = 0.60
    loop.trust_engine.MAX_REDEMPTION_CYCLES = 20

    # Reproducible routing decisions
    random.seed(2024)

    # Initialize executor — the ONLY domain-specific component
    executor = FinanceAllocationExecutor()

    # Initialize agents via the kernel
    agents = create_agents()

    # ── Tracking state (for frontend output, NOT for governance) ──
    portfolio_value = float(STARTING_PORTFOLIO)
    benchmark_value = float(STARTING_PORTFOLIO)
    peak_portfolio = portfolio_value
    peak_benchmark = benchmark_value
    max_drawdown_portfolio = 0.0
    max_drawdown_benchmark = 0.0
    cumulative_returns = {aid: 0.0 for aid in AGENTS}
    weeks_suppressed = {aid: 0 for aid in AGENTS}
    weeks_led = {aid: 0 for aid in AGENTS}

    timeline = []
    all_events = []
    mutation_events_list = []

    # ── Payload comparison examples ───────────────────────────
    sample_payloads = {
        "finance": None,
        "lending": {
            "task": {
                "id": "LOAN_2847",
                "impact": 0.72,
                "urgency": 0.85,
                "risk": 0.45,
                "metadata": {
                    "amount": 25000,
                    "grade": "C",
                    "dti": 18.5,
                    "purpose": "debt_consolidation"
                }
            },
            "result": {
                "task_id": "LOAN_2847",
                "agent_id": "growth_underwriter",
                "success": False,
                "metadata": {
                    "decision": "APPROVED",
                    "outcome": "DEFAULTED",
                    "risk_score": 0.45,
                    "loss_amount": 8200
                }
            },
            "governance_response": {
                "trust_update": {"growth_underwriter": 0.71},
                "status": "probation",
                "mutation": {"trust_threshold": 0.73}
            }
        }
    }

    # ── Main simulation loop ──────────────────────────────────
    for week_idx, week_data in enumerate(weeks_data):
        week_num = week_data["week"]
        date = week_data["date"]
        regime = week_data["regime"]
        benchmark_return = week_data["benchmark_return"]

        week_events = []

        # Regime shift event
        if week_num == 53:
            week_events.append({
                "type": "regime_shift",
                "color": "purple",
                "text": (f"[WEEK {week_num:02d}] REGIME SHIFT DETECTED — "
                         f"Stress phase begins — Rate-rise/inflation shock")
            })

        # ── 1. Create tasks from market data ──────────────────
        tasks = create_week_tasks(week_data, week_num)

        # Snapshot thresholds before cycle (for event logging)
        prev_trust_threshold = loop.trust_engine.trust_threshold
        prev_suppression_threshold = loop.trust_engine.suppression_threshold

        # ── 2. Execute governance cycle (REAL KERNEL) ─────────
        # This single call handles:
        #   - Task prioritization (Optimus)
        #   - Agent assignment (TrustEngine — trust-ranked routing)
        #   - Task execution (FinanceAllocationExecutor)
        #   - Trust score updates (LearningEngine — asymmetric)
        #   - Threshold mutation (MutationEngine — Claim 5)
        #   - Reflection (RIF)
        #   - State persistence (SQLite)
        try:
            cycle_result = loop.execute_cycle(
                tasks, agents, executor, run_id=f"FINANCE_{week_num:03d}"
            )
        except (CircuitBreakerTriggered, NoAgentsAvailable) as e:
            # Circuit breaker: all agents below threshold
            week_events.append({
                "type": "circuit_breaker",
                "color": "red",
                "text": (f"[WEEK {week_num:02d}] CIRCUIT BREAKER — "
                         f"{e} — recovering agents")
            })

            # Recovery: nudge agents above suppression threshold
            sup_thresh = loop.trust_engine.suppression_threshold
            for a in agents.values():
                if a.trust_score < sup_thresh + 0.01:
                    a.trust_score = sup_thresh + 0.01
                    a.status = "active"
            loop.trust_engine.suppressed_agents.clear()
            loop.trust_engine.probation_agents.clear()

            # Record timeline entry for circuit breaker week
            timeline.append({
                "week": week_num,
                "date": date,
                "regime": regime,
                "agents": {
                    aid: {
                        "trust": round(agents[aid].trust_score, 4),
                        "authority_weight": round(1.0 / len(AGENTS), 4),
                        "status": "active",
                        "weekly_return": 0.0,
                        "benchmark_delta": 0.0,
                        "cumulative_return": round(cumulative_returns[aid], 6),
                        "allocation": AGENTS[aid]["allocation"],
                    }
                    for aid in AGENTS
                },
                "portfolio_value": round(portfolio_value, 0),
                "benchmark_value": round(benchmark_value, 0),
                "portfolio_return": round(benchmark_return, 6),
                "benchmark_return": round(benchmark_return, 6),
                "outperformance_dollar": round(portfolio_value - benchmark_value, 0),
                "outperformance_pct": round(
                    (portfolio_value - benchmark_value) / STARTING_PORTFOLIO * 100, 2
                ),
                "events": week_events,
                "regime_shift": week_num == 53,
                "suppression_floor": round(loop.trust_engine.suppression_threshold, 3),
                "max_drawdown_portfolio": round(max_drawdown_portfolio, 4),
                "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
            })
            all_events.extend(week_events)
            continue

        # ── 3. Read back kernel state ─────────────────────────
        # All governance decisions come FROM the kernel, not custom code.

        # Extract per-agent results from the cycle
        agent_results = {}
        for r in cycle_result["results"]:
            agent_results[r.agent_id] = r

        # Read trust scores directly from agent objects (updated by kernel)
        # Read suppression/probation status from TrustEngine
        agent_statuses = {}
        for aid in AGENTS:
            agent_statuses[aid] = get_agent_status_from_kernel(
                aid, agents, loop.trust_engine
            )

        # ── 4. Derive authority weights from kernel state ─────
        authority_weights = derive_authority_weights(agents, loop.trust_engine)

        # ── 5. Generate governance events from kernel state ───

        # Suppression events
        for aid in AGENTS:
            prev_entry = timeline[-1] if timeline else None
            prev_status = (
                prev_entry["agents"][aid]["status"] if prev_entry else "active"
            )
            curr_status = agent_statuses[aid]

            if curr_status == "suppressed" and prev_status != "suppressed":
                week_events.append({
                    "type": "suppression",
                    "color": "red",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"SUPPRESSED — trust {agents[aid].trust_score:.2f} "
                             f"< threshold {loop.trust_engine.suppression_threshold:.2f} — "
                             f"authority reallocated to remaining agents")
                })
            elif curr_status == "probation" and prev_status == "suppressed":
                week_events.append({
                    "type": "redemption",
                    "color": "green",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"redemption — restored to PROBATION — "
                             f"trust {agents[aid].trust_score:.2f}")
                })
            elif curr_status == "probation" and prev_status == "active":
                week_events.append({
                    "type": "probation",
                    "color": "amber",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"-> PROBATION — trust {agents[aid].trust_score:.2f}")
                })
            elif curr_status == "active" and prev_status in ("suppressed", "probation"):
                week_events.append({
                    "type": "recovery",
                    "color": "green",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"restored to ACTIVE — trust {agents[aid].trust_score:.2f}")
                })

            if curr_status == "suppressed":
                weeks_suppressed[aid] += 1

        # Trust change events
        for aid in AGENTS:
            if aid in agent_results:
                r = agent_results[aid]
                delta = r.metadata.get("benchmark_delta", 0.0)
                trust_val = agents[aid].trust_score
                if r.success:
                    week_events.append({
                        "type": "trust_increase",
                        "color": "blue",
                        "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                 f"outperformed benchmark {delta:+.2%} — "
                                 f"trust now {trust_val:.2f}")
                    })
                elif not r.success:
                    color = "red" if abs(delta) > 0.006 else "amber"
                    week_events.append({
                        "type": "trust_decrease_severe" if abs(delta) > 0.006 else "trust_decrease_moderate",
                        "color": color,
                        "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                 f"underperformed benchmark {delta:+.2%} — "
                                 f"trust now {trust_val:.2f}")
                    })

        # Drift detection events (from kernel)
        for aid, is_drifting in loop.trust_engine.drift_warnings.items():
            if is_drifting:
                week_events.append({
                    "type": "drift_detected",
                    "color": "amber",
                    "text": (f"[WEEK {week_num:02d}] DRIFT DETECTED: "
                             f"{AGENTS.get(aid, {}).get('label', aid)}")
                })

        # Mutation events (from kernel)
        mutation = cycle_result.get("mutation", {})
        new_trust_threshold = mutation.get("trust_threshold", prev_trust_threshold)
        new_suppression_threshold = mutation.get(
            "suppression_threshold", prev_suppression_threshold
        )
        if abs(new_suppression_threshold - prev_suppression_threshold) > 0.001:
            mutation_events_list.append({
                "week": week_num,
                "old_threshold": round(prev_suppression_threshold, 3),
                "new_threshold": round(new_suppression_threshold, 3),
            })
            direction = "tightened" if new_suppression_threshold > prev_suppression_threshold else "loosened"
            week_events.append({
                "type": "mutation",
                "color": "purple",
                "text": (f"[WEEK {week_num:02d}] THRESHOLD MUTATION — "
                         f"Suppression floor {direction}: "
                         f"{prev_suppression_threshold:.2f} -> "
                         f"{new_suppression_threshold:.2f}")
            })

        # ── 6. Compute portfolio return from authority weights ─
        # Portfolio return = weighted sum of agent returns using kernel-derived weights
        agent_returns = {}
        agent_deltas = {}
        for aid in AGENTS:
            if aid in agent_results:
                agent_returns[aid] = agent_results[aid].metadata.get("weekly_return", 0.0)
                agent_deltas[aid] = agent_results[aid].metadata.get("benchmark_delta", 0.0)
            else:
                agent_returns[aid] = 0.0
                agent_deltas[aid] = 0.0

        portfolio_return = sum(
            authority_weights[aid] * agent_returns[aid]
            for aid in AGENTS
        )

        portfolio_value *= (1.0 + portfolio_return)
        benchmark_value *= (1.0 + benchmark_return)

        # Drawdowns
        peak_portfolio = max(peak_portfolio, portfolio_value)
        peak_benchmark = max(peak_benchmark, benchmark_value)
        dd_portfolio = (portfolio_value - peak_portfolio) / peak_portfolio
        dd_benchmark = (benchmark_value - peak_benchmark) / peak_benchmark
        max_drawdown_portfolio = min(max_drawdown_portfolio, dd_portfolio)
        max_drawdown_benchmark = min(max_drawdown_benchmark, dd_benchmark)

        # Cumulative returns
        for aid in AGENTS:
            cumulative_returns[aid] += agent_returns.get(aid, 0.0)

        # Track who leads
        max_weight_agent = max(authority_weights, key=authority_weights.get)
        weeks_led[max_weight_agent] += 1

        # ── Store payload example on week 1 ───────────────────
        if week_num == 1 and "growth" in agent_results:
            r = agent_results["growth"]
            sample_payloads["finance"] = {
                "task": {
                    "id": f"ALLOC_001_growth",
                    "impact": round(min(1.0, abs(agent_deltas.get("growth", 0)) * 100), 3),
                    "urgency": 0.7,
                    "risk": round(max(0.1, 0.5 - agent_deltas.get("growth", 0) * 50), 3),
                    "metadata": {
                        "weekly_return": round(agent_returns.get("growth", 0), 6),
                        "benchmark_delta": round(agent_deltas.get("growth", 0), 6),
                        "regime": regime,
                        "allocation": AGENTS["growth"]["allocation"]
                    }
                },
                "result": {
                    "task_id": f"ALLOC_001_growth",
                    "agent_id": "growth",
                    "success": r.success,
                    "metadata": {
                        "decision": r.metadata.get("decision"),
                        "outcome": r.metadata.get("outcome"),
                        "benchmark_delta": round(agent_deltas.get("growth", 0), 6),
                        "authority_weight": authority_weights.get("growth", 0)
                    }
                },
                "governance_response": {
                    "trust_update": {"growth": round(agents["growth"].trust_score, 3)},
                    "status": agent_statuses["growth"],
                    "mutation": {
                        "suppression_threshold": round(
                            loop.trust_engine.suppression_threshold, 3
                        )
                    }
                }
            }

        # ── Store week record ─────────────────────────────────
        week_record = {
            "week": week_num,
            "date": date,
            "regime": regime,
            "agents": {},
            "portfolio_value": round(portfolio_value, 0),
            "benchmark_value": round(benchmark_value, 0),
            "portfolio_return": round(portfolio_return, 6),
            "benchmark_return": round(benchmark_return, 6),
            "outperformance_dollar": round(portfolio_value - benchmark_value, 0),
            "outperformance_pct": round(
                (portfolio_value - benchmark_value) / STARTING_PORTFOLIO * 100, 2
            ),
            "events": week_events,
            "regime_shift": week_num == 53,
            "suppression_floor": round(loop.trust_engine.suppression_threshold, 3),
            "max_drawdown_portfolio": round(max_drawdown_portfolio, 4),
            "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
        }

        for aid in AGENTS:
            week_record["agents"][aid] = {
                "trust": round(agents[aid].trust_score, 4),
                "authority_weight": authority_weights[aid],
                "status": agent_statuses[aid],
                "weekly_return": round(agent_returns.get(aid, 0.0), 6),
                "benchmark_delta": round(agent_deltas.get(aid, 0.0), 6),
                "cumulative_return": round(cumulative_returns[aid], 6),
                "allocation": AGENTS[aid]["allocation"],
            }

        timeline.append(week_record)
        all_events.extend(week_events)

        # Print progress
        if week_num % 10 == 0 or week_num == 1 or week_num == 53:
            statuses = " | ".join(
                f"{aid}: {agents[aid].trust_score:.2f} ({agent_statuses[aid][:3].upper()})"
                for aid in AGENTS
            )
            outperf = portfolio_value - benchmark_value
            print(f"  Week {week_num:3d} [{regime:6s}] "
                  f"${portfolio_value:>12,.0f}  "
                  f"vs BM: ${outperf:>+10,.0f}  "
                  f"| {statuses}")

    # ── Compute summary ───────────────────────────────────────
    bull_weeks = [w for w in timeline if w["regime"] == "bull"]
    stress_weeks = [w for w in timeline if w["regime"] == "stress"]

    growth_suppressed_weeks = [
        w["week"] for w in timeline
        if w["agents"]["growth"]["status"] == "suppressed"
    ]
    risk_led_weeks = [
        w["week"] for w in timeline
        if w["agents"]["risk"]["authority_weight"] == max(
            w["agents"][a]["authority_weight"] for a in AGENTS
        )
    ]

    # Outperformance attribution
    suppression_outperformance = sum(
        w["portfolio_return"] - w["benchmark_return"]
        for w in timeline
        if w["agents"]["growth"]["status"] == "suppressed"
    )
    total_outperformance = portfolio_value - benchmark_value

    suppression_attribution = round(
        suppression_outperformance * STARTING_PORTFOLIO, 0
    )
    elevation_attribution = round(
        sum(
            max(0, w["agents"]["risk"]["authority_weight"] - 1/3)
            * w["agents"]["risk"]["weekly_return"]
            for w in stress_weeks
        ) * STARTING_PORTFOLIO, 0
    )
    mutation_attribution = round(
        total_outperformance - suppression_attribution - elevation_attribution, 0
    )

    # Agent regime performance
    agent_regime_perf = {}
    for aid in AGENTS:
        bull_ret = sum(w["agents"][aid]["weekly_return"] for w in bull_weeks)
        stress_ret = sum(w["agents"][aid]["weekly_return"] for w in stress_weeks)
        active_wks = sum(1 for w in timeline if w["agents"][aid]["status"] == "active")
        agent_regime_perf[aid] = {
            "bull_return": round(bull_ret * 100, 2),
            "stress_return": round(stress_ret * 100, 2),
            "full_return": round((bull_ret + stress_ret) * 100, 2),
            "weeks_active": active_wks,
        }
    bm_bull = sum(w["benchmark_return"] for w in bull_weeks)
    bm_stress = sum(w["benchmark_return"] for w in stress_weeks)
    agent_regime_perf["benchmark"] = {
        "bull_return": round(bm_bull * 100, 2),
        "stress_return": round(bm_stress * 100, 2),
        "full_return": round((bm_bull + bm_stress) * 100, 2),
        "weeks_active": len(timeline),
    }

    dd_reduction = 0.0
    if max_drawdown_benchmark != 0:
        dd_reduction = round(
            (1 - max_drawdown_portfolio / max_drawdown_benchmark) * 100, 0
        )

    # Kernel statistics from persistent state
    db_stats = state.get_statistics()

    summary = {
        "final_portfolio_value": round(portfolio_value, 0),
        "final_benchmark_value": round(benchmark_value, 0),
        "total_outperformance_dollar": round(total_outperformance, 0),
        "total_outperformance_pct": round(
            (portfolio_value / benchmark_value - 1) * 100, 2
        ),
        "max_drawdown_governed": round(max_drawdown_portfolio, 4),
        "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
        "drawdown_reduction_pct": dd_reduction,
        "weeks_growth_suppressed": len(growth_suppressed_weeks),
        "weeks_risk_led": len(risk_led_weeks),
        "total_governance_events": len(all_events),
        "regime_shift_week": 53,
        "total_weeks": len(timeline),
        "starting_portfolio": STARTING_PORTFOLIO,
        "agent_regime_performance": agent_regime_perf,
        "attribution": {
            "suppression_of_growth": suppression_attribution,
            "elevation_of_risk": elevation_attribution,
            "threshold_mutation": mutation_attribution,
        },
        "mutation_events": mutation_events_list,
        "payload_comparison": sample_payloads,
        "governance_kernel": {
            "engine": "GovernanceLoop (syntropiq.governance.loop)",
            "trust_engine": "SyntropiqTrustEngine (asymmetric learning: +0.02/-0.05)",
            "mutation_engine": "MutationEngine (Patent Claim 5)",
            "routing_mode": "competitive",
            "total_executions": db_stats["total_executions"],
            "overall_success_rate": db_stats["success_rate"],
            "valid_reflections": db_stats["valid_reflections"],
            "final_trust_threshold": round(loop.trust_engine.trust_threshold, 4),
            "final_suppression_threshold": round(
                loop.trust_engine.suppression_threshold, 4
            ),
        },
        "governance_parameters": {
            "starting_trust": STARTING_TRUST,
            "initial_trust_threshold": 0.55,
            "initial_suppression_threshold": 0.40,
            "drift_delta": 0.08,
            "mutation_rate": 0.015,
            "target_success_rate": 0.60,
            "max_redemption_cycles": 20,
            "asymmetric_reward": 0.02,
            "asymmetric_penalty": 0.05,
            "routing_mode": "competitive",
        },
    }

    output = {"summary": summary, "timeline": timeline}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # ── Print summary ─────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  SIMULATION COMPLETE — Real Syntropiq Kernel")
    print(f"{'='*78}")
    print(f"\n  Portfolio:      ${portfolio_value:>14,.0f}")
    print(f"  Benchmark:      ${benchmark_value:>14,.0f}")
    print(f"  Outperformance: ${total_outperformance:>+14,.0f} "
          f"({summary['total_outperformance_pct']:+.2f}%)")
    print(f"\n  Max Drawdown:")
    print(f"    Governed:     {max_drawdown_portfolio:>+8.2%}")
    print(f"    Benchmark:    {max_drawdown_benchmark:>+8.2%}")
    if dd_reduction > 0:
        print(f"    Reduction:    {dd_reduction:.0f}% less drawdown")
    print(f"\n  Governance (Real Kernel):")
    print(f"    Total executions:  {db_stats['total_executions']}")
    print(f"    Success rate:      {db_stats['success_rate']:.1%}")
    print(f"    Reflections:       {db_stats['valid_reflections']}")
    print(f"    Events:            {len(all_events)}")
    print(f"    Growth suppressed: {len(growth_suppressed_weeks)} weeks")
    print(f"    Risk led:          {len(risk_led_weeks)} weeks")
    print(f"    Mutations:         {len(mutation_events_list)}")
    print(f"    Trust threshold:   {loop.trust_engine.trust_threshold:.3f}")
    print(f"    Suppression thresh:{loop.trust_engine.suppression_threshold:.3f}")
    print(f"\n  Output: {OUTPUT_PATH}")

    return output


if __name__ == "__main__":
    run_simulation()
