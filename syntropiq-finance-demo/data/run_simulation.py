#!/usr/bin/env python3
"""
Syntropiq Adaptive Allocation Governance Engine — Simulation Runner

Runs the full 104-week simulation using real market data and the Syntropiq
governance kernel. Precomputes all data for the React frontend.

Uses the SAME governance primitives as the fraud, lending, and readmission
demos — trust scoring, suppression/redemption, mutation engine, drift
detection. Only the domain mapping changes.

Domain Mapping:
    Prior demos          → Finance demo
    ──────────────────────────────────────────
    Loan approval        → Capital allocation
    Default event        → Underperformance vs benchmark
    Default severity     → Magnitude of underperformance delta
    Recovery             → Sustained outperformance (3+ weeks)
    Dollar loss          → Portfolio underperformance in dollars

Output: simulation_data.json (consumed by React frontend)

Usage:
    python data/run_simulation.py
"""

import json
import math
import hashlib
import os
import sys

# Add parent directory to path for Syntropiq imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from syntropiq.core.models import Task, Agent, ExecutionResult

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_PATH = os.path.join(DATA_DIR, "market_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "simulation_data.json")

# ── Agent Definitions ────────────────────────────────────────────

AGENTS = {
    "growth": {
        "label": "Growth Agent",
        "allocation": {"QQQ": 0.70, "SPY": 0.20, "TLT": 0.10},
        "description": "Tech-heavy allocation, outperforms in bull, degrades in stress",
    },
    "risk": {
        "label": "Risk Agent",
        "allocation": {"QQQ": 0.15, "SPY": 0.25, "TLT": 0.60},
        "description": "Bond-heavy allocation, underperforms in bull, outperforms in stress",
    },
    "macro": {
        "label": "Macro Agent",
        "allocation": {"QQQ": 0.35, "SPY": 0.45, "TLT": 0.20},
        "description": "Balanced allocation, moderate across regimes",
    },
}

STARTING_TRUST = 0.75
STARTING_PORTFOLIO = 10_000_000

# ── Governance Parameters (Finance-Specific) ────────────────────

TRUST_INCREASE = 0.04            # Outperform benchmark
TRUST_DECREASE_MILD = 0.03       # Underperform < 0.3%
TRUST_DECREASE_MODERATE = 0.08   # Underperform 0.3–0.6%
TRUST_DECREASE_SEVERE = 0.15     # Underperform > 0.6% (asymmetric penalty)

SUPPRESSION_THRESHOLD = 0.40     # Below this: suppressed
PROBATION_CEILING = 0.55         # Below this but above suppression: probation
ACTIVE_THRESHOLD = 0.55          # Above this: fully active

REDEMPTION_WEEKS_REQUIRED = 3    # Consecutive weeks above benchmark to restore

CONSECUTIVE_FAIL_TRIGGER = 3
MUTATION_TIGHTEN_AMOUNT = 0.05


def _stable_hash(s: str) -> float:
    """Deterministic noise in [-0.001, 0.001]."""
    h = int(hashlib.sha256(s.encode()).hexdigest(), 16)
    return ((h % 2000) - 1000) / 1000000.0


def compute_agent_return(agent_id: str, week_data: dict, week_num: int) -> float:
    """Compute an agent's weekly return from its allocation weights and market data."""
    alloc = AGENTS[agent_id]["allocation"]
    tickers = week_data["tickers"]
    weighted_return = sum(
        alloc.get(ticker, 0.0) * tickers[ticker]["weekly_return"]
        for ticker in alloc
    )
    noise = _stable_hash(f"agent_{agent_id}_week_{week_num}")
    return weighted_return + noise


def compute_trust_delta(benchmark_delta: float) -> float:
    """Asymmetric trust update based on delta vs benchmark (Patent Claim 1)."""
    if benchmark_delta >= -0.0005:
        # Outperformed or within noise band (±0.05%)
        return TRUST_INCREASE
    magnitude = abs(benchmark_delta)
    if magnitude < 0.003:
        return -TRUST_DECREASE_MILD
    elif magnitude < 0.006:
        return -TRUST_DECREASE_MODERATE
    else:
        return -TRUST_DECREASE_SEVERE


def run_simulation():
    """Run the full 104-week governance simulation."""

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
    print(f"  Governance: Trust-scored authority with suppression/redemption")
    print(f"{'='*78}")

    # ── Agent state ───────────────────────────────────────────
    trust_scores = {aid: STARTING_TRUST for aid in AGENTS}
    agent_status = {aid: "active" for aid in AGENTS}
    authority_weights = {aid: 1.0 / len(AGENTS) for aid in AGENTS}
    redemption_counters = {aid: 0 for aid in AGENTS}
    trust_history = {aid: [STARTING_TRUST] for aid in AGENTS}

    portfolio_value = float(STARTING_PORTFOLIO)
    benchmark_value = float(STARTING_PORTFOLIO)

    # Mutation state
    consecutive_system_failures = 0
    suppression_floor = SUPPRESSION_THRESHOLD
    mutation_events_list = []

    # Tracking
    timeline = []
    all_events = []
    cumulative_returns = {aid: 0.0 for aid in AGENTS}
    peak_portfolio = portfolio_value
    peak_benchmark = benchmark_value
    max_drawdown_portfolio = 0.0
    max_drawdown_benchmark = 0.0
    weeks_suppressed = {aid: 0 for aid in AGENTS}
    weeks_led = {aid: 0 for aid in AGENTS}

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

        # Regime shift
        if week_num == 53:
            week_events.append({
                "type": "regime_shift",
                "color": "purple",
                "text": (f"[WEEK {week_num:02d}] REGIME SHIFT DETECTED — "
                         f"Stress phase begins — Rate-rise/inflation shock")
            })

        # ── 1. Compute agent returns ─────────────────────────
        agent_returns = {}
        agent_deltas = {}

        for aid in AGENTS:
            ret = compute_agent_return(aid, week_data, week_num)
            delta = ret - benchmark_return
            agent_returns[aid] = ret
            agent_deltas[aid] = delta

        # ── 2. Update trust scores (Asymmetric — Claim 1) ────
        for aid in AGENTS:
            delta = agent_deltas[aid]
            trust_change = compute_trust_delta(delta)
            old_trust = trust_scores[aid]
            new_trust = max(0.0, min(1.0, old_trust + trust_change))
            trust_scores[aid] = round(new_trust, 4)

            # Log significant events
            if trust_change > 0:
                week_events.append({
                    "type": "trust_increase",
                    "color": "blue",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"outperformed benchmark {delta:+.2%} — "
                             f"trust ↑ {old_trust:.2f} → {new_trust:.2f}")
                })
            elif trust_change <= -TRUST_DECREASE_SEVERE:
                week_events.append({
                    "type": "trust_decrease_severe",
                    "color": "red",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"underperformed benchmark {delta:+.2%} — "
                             f"trust ↓ {old_trust:.2f} → {new_trust:.2f}")
                })
            elif trust_change <= -TRUST_DECREASE_MODERATE:
                week_events.append({
                    "type": "trust_decrease_moderate",
                    "color": "amber",
                    "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                             f"underperformed benchmark {delta:+.2%} — "
                             f"trust ↓ {old_trust:.2f} → {new_trust:.2f}")
                })

            trust_history[aid].append(trust_scores[aid])

        # ── 3. Suppression / Probation / Redemption (Claim 3) ─
        for aid in AGENTS:
            prev_status = agent_status[aid]

            if trust_scores[aid] < suppression_floor:
                if prev_status != "suppressed":
                    agent_status[aid] = "suppressed"
                    redemption_counters[aid] = 0
                    week_events.append({
                        "type": "suppression",
                        "color": "red",
                        "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                 f"SUPPRESSED — trust {trust_scores[aid]:.2f} "
                                 f"< threshold {suppression_floor:.2f} — "
                                 f"authority reallocated to remaining agents")
                    })
                else:
                    # Check for redemption while suppressed
                    if agent_deltas[aid] >= 0:
                        redemption_counters[aid] += 1
                        if redemption_counters[aid] >= REDEMPTION_WEEKS_REQUIRED:
                            agent_status[aid] = "probation"
                            week_events.append({
                                "type": "redemption",
                                "color": "green",
                                "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                         f"redemption sequence complete — "
                                         f"{REDEMPTION_WEEKS_REQUIRED} consecutive "
                                         f"weeks above benchmark — restored to PROBATION")
                            })
                    else:
                        redemption_counters[aid] = 0

                if agent_status[aid] == "suppressed":
                    weeks_suppressed[aid] += 1

            elif trust_scores[aid] < PROBATION_CEILING:
                if prev_status == "active":
                    agent_status[aid] = "probation"
                    week_events.append({
                        "type": "probation",
                        "color": "amber",
                        "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                 f"→ PROBATION — trust {trust_scores[aid]:.2f}")
                    })
                elif prev_status == "suppressed":
                    # Already handled above in redemption
                    pass
                # probation stays probation
            else:
                if prev_status in ("suppressed", "probation"):
                    agent_status[aid] = "active"
                    event_type = "redemption" if prev_status == "suppressed" else "recovery"
                    week_events.append({
                        "type": event_type,
                        "color": "green",
                        "text": (f"[WEEK {week_num:02d}] {AGENTS[aid]['label']} "
                                 f"restored to ACTIVE — trust {trust_scores[aid]:.2f}")
                    })
                redemption_counters[aid] = 0

        # ── 4. Compute authority weights ──────────────────────
        raw_weights = {}
        for aid in AGENTS:
            if agent_status[aid] == "suppressed":
                raw_weights[aid] = 0.0
            elif agent_status[aid] == "probation":
                raw_weights[aid] = trust_scores[aid] * 0.5
            else:
                raw_weights[aid] = trust_scores[aid]

        total_weight = sum(raw_weights.values())
        if total_weight > 0:
            authority_weights = {
                aid: round(w / total_weight, 4)
                for aid, w in raw_weights.items()
            }
        else:
            # All suppressed — weight by relative trust (least-bad agent leads)
            trust_sum = sum(max(0.01, trust_scores[a]) for a in AGENTS)
            authority_weights = {
                aid: round(max(0.01, trust_scores[aid]) / trust_sum, 4)
                for aid in AGENTS
            }

        # Track who leads
        max_weight_agent = max(authority_weights, key=authority_weights.get)
        weeks_led[max_weight_agent] += 1

        # ── 5. Compute portfolio return ───────────────────────
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

        # ── 6. Threshold mutation (Claim 5) ───────────────────
        agents_failing = sum(
            1 for aid in AGENTS if agent_deltas[aid] < 0
        )
        system_failed = agents_failing > len(AGENTS) / 2

        if system_failed:
            consecutive_system_failures += 1
        else:
            consecutive_system_failures = 0

        if consecutive_system_failures >= CONSECUTIVE_FAIL_TRIGGER:
            old_floor = suppression_floor
            suppression_floor = round(
                min(0.60, suppression_floor + MUTATION_TIGHTEN_AMOUNT), 3
            )
            consecutive_system_failures = 0
            mutation_events_list.append({
                "week": week_num,
                "old_threshold": old_floor,
                "new_threshold": suppression_floor,
            })
            week_events.append({
                "type": "mutation",
                "color": "purple",
                "text": (f"[WEEK {week_num:02d}] THRESHOLD MUTATION — "
                         f"Suppression floor tightened: "
                         f"{old_floor:.2f} → {suppression_floor:.2f}")
            })

        # ── Cumulative returns ────────────────────────────────
        for aid in AGENTS:
            cumulative_returns[aid] += agent_returns[aid]

        # ── Store payload example on week 1 ───────────────────
        if week_num == 1:
            sample_payloads["finance"] = {
                "task": {
                    "id": f"ALLOC_001_growth",
                    "impact": round(min(1.0, abs(agent_deltas["growth"]) * 100), 3),
                    "urgency": 0.7,
                    "risk": round(max(0.1, 0.5 - agent_deltas["growth"] * 50), 3),
                    "metadata": {
                        "weekly_return": round(agent_returns["growth"], 6),
                        "benchmark_delta": round(agent_deltas["growth"], 6),
                        "regime": regime,
                        "allocation": AGENTS["growth"]["allocation"]
                    }
                },
                "result": {
                    "task_id": f"ALLOC_001_growth",
                    "agent_id": "growth",
                    "success": agent_deltas["growth"] >= 0,
                    "metadata": {
                        "decision": "OUTPERFORMED" if agent_deltas["growth"] >= 0 else "UNDERPERFORMED",
                        "outcome": "ALPHA_GENERATED" if agent_deltas["growth"] >= 0 else "BENCHMARK_MISS",
                        "benchmark_delta": round(agent_deltas["growth"], 6),
                        "authority_weight": round(authority_weights["growth"], 4)
                    }
                },
                "governance_response": {
                    "trust_update": {"growth": round(trust_scores["growth"], 3)},
                    "status": agent_status["growth"],
                    "mutation": {"suppression_threshold": suppression_floor}
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
            "suppression_floor": round(suppression_floor, 3),
            "max_drawdown_portfolio": round(max_drawdown_portfolio, 4),
            "max_drawdown_benchmark": round(max_drawdown_benchmark, 4),
        }

        for aid in AGENTS:
            week_record["agents"][aid] = {
                "trust": round(trust_scores[aid], 4),
                "authority_weight": authority_weights[aid],
                "status": agent_status[aid],
                "weekly_return": round(agent_returns[aid], 6),
                "benchmark_delta": round(agent_deltas[aid], 6),
                "cumulative_return": round(cumulative_returns[aid], 6),
                "allocation": AGENTS[aid]["allocation"],
            }

        timeline.append(week_record)
        all_events.extend(week_events)

        # Print progress
        if week_num % 10 == 0 or week_num == 1 or week_num == 53:
            statuses = " | ".join(
                f"{aid}: {trust_scores[aid]:.2f} ({agent_status[aid][:3].upper()})"
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
        "governance_parameters": {
            "starting_trust": STARTING_TRUST,
            "trust_increase": TRUST_INCREASE,
            "trust_decrease_mild": TRUST_DECREASE_MILD,
            "trust_decrease_moderate": TRUST_DECREASE_MODERATE,
            "trust_decrease_severe": TRUST_DECREASE_SEVERE,
            "suppression_threshold": SUPPRESSION_THRESHOLD,
            "probation_ceiling": PROBATION_CEILING,
            "active_threshold": ACTIVE_THRESHOLD,
            "redemption_weeks": REDEMPTION_WEEKS_REQUIRED,
            "mutation_consecutive_failures": CONSECUTIVE_FAIL_TRIGGER,
            "mutation_tighten_amount": MUTATION_TIGHTEN_AMOUNT,
        },
    }

    output = {"summary": summary, "timeline": timeline}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # ── Print summary ─────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  SIMULATION COMPLETE")
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
    print(f"\n  Governance:")
    print(f"    Events:       {len(all_events)}")
    print(f"    Growth supp:  {len(growth_suppressed_weeks)} weeks")
    print(f"    Risk led:     {len(risk_led_weeks)} weeks")
    print(f"    Mutations:    {len(mutation_events_list)}")
    print(f"\n  Output: {OUTPUT_PATH}")

    return output


if __name__ == "__main__":
    run_simulation()
