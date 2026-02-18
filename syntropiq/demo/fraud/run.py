"""
Syntropiq Fraud Detection Demo — Live Governance Simulation

Streams realistic payment transactions through 3 AI fraud detection agents
governed by Syntropiq's trust engine. One agent gradually drifts, passing
riskier transactions. Syntropiq catches it.

Usage:
    python -m syntropiq.demo.fraud.run
    python -m syntropiq.demo.fraud.run --cycles 30 --batch-size 8
    python -m syntropiq.demo.fraud.run --csv path/to/ieee_cis_sample.csv
    python -m syntropiq.demo.fraud.run --output results.json

What investors see:
    - Trust scores diverging as one agent starts missing fraud
    - Suppression firing when the drifting agent crosses the threshold
    - Mutation engine tightening system-wide thresholds
    - Redemption as the agent earns trust back on safe transactions
    - Dollar-denominated prevented losses on real transaction amounts
"""

import argparse
import json
import sys
from typing import Dict, List, Any

from syntropiq.core.models import Agent
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.demo.fraud.data import (
    generate_fraud_batch, RealDataPool,
)
from syntropiq.demo.fraud.executor import FraudDetectionExecutor


# ── Agent Definitions ─────────────────────────────────────────

def create_agents() -> Dict[str, Agent]:
    """
    Three fraud detection agents with different sensitivity profiles.

    rule_engine: Conservative rule-based system — flags aggressively
    ml_scorer:   ML model with moderate sensitivity
    ensemble:    Ensemble approach — THIS ONE DRIFTS
    """
    return {
        "rule_engine": Agent(
            id="rule_engine",
            trust_score=0.90,
            capabilities=["fraud_detection"],
            status="active",
        ),
        "ml_scorer": Agent(
            id="ml_scorer",
            trust_score=0.88,
            capabilities=["fraud_detection"],
            status="active",
        ),
        "ensemble": Agent(
            id="ensemble",
            trust_score=0.86,
            capabilities=["fraud_detection"],
            status="active",
        ),
    }


# fraud_threshold = max risk_score the agent will PASS (allow through)
# Lower = more conservative (flags more)
AGENT_PROFILES = {
    "rule_engine": 0.25,   # Only passes lowest-risk (T1)
    "ml_scorer":   0.35,   # Passes T1, some T2
    "ensemble":    0.40,   # Passes T1-T2 — will drift to 0.85+
}

DRIFT_AGENT = "ensemble"


# ── Output Formatting ─────────────────────────────────────────

def format_header():
    print("\n" + "=" * 78)
    print("  SYNTROPIQ GOVERNANCE DEMO — Fraud Detection (IEEE-CIS)")
    print("  Trust-Governed Execution with Real Transaction Data")
    print("=" * 78)


def format_cycle_header(cycle: int, num_cycles: int, phase: str):
    print(f"\n{'─' * 78}")
    print(f"  CYCLE {cycle + 1}/{num_cycles}  │  Phase: {phase}")
    print(f"{'─' * 78}")


def format_trust_scores(agents: Dict[str, Agent], drift_threshold: float):
    print("\n  Agent Trust Scores:")
    for aid, agent in sorted(agents.items(), key=lambda x: -x[1].trust_score):
        bar_len = int(agent.trust_score * 40)
        bar = "#" * bar_len + "." * (40 - bar_len)
        drift_marker = " << DRIFTING" if aid == DRIFT_AGENT else ""
        status = agent.status.upper()
        print(f"    {aid:<14} [{bar}] {agent.trust_score:.3f}  ({status}){drift_marker}")
    print(f"    {'':14} drift agent threshold: {drift_threshold:.3f}")


def format_execution_summary(result: Dict[str, Any]):
    stats = result["statistics"]
    total = stats["tasks_executed"]
    ok = stats["successes"]
    fail = stats["failures"]
    rate = ok / total if total else 0

    print(f"\n  Execution: {ok}/{total} correct ({rate:.0%})")

    missed_fraud = [
        r for r in result["results"]
        if r.metadata.get("outcome", "").startswith("MISSED_FRAUD")
    ]
    if missed_fraud:
        total_loss = sum(r.metadata.get("tx_amount", 0) for r in missed_fraud)
        print(f"  !! {len(missed_fraud)} missed fraud — ${total_loss:,.0f} potential loss")


def format_governance_events(
    loop: GovernanceLoop,
    result: Dict[str, Any],
    prev_thresholds: Dict[str, float],
):
    events = []

    suppressed = loop.trust_engine.suppressed_agents
    if suppressed:
        for aid, cycles in suppressed.items():
            events.append(f"SUPPRESSED: {aid} (redemption cycle {cycles})")

    probation = loop.trust_engine.probation_agents
    for aid in probation:
        if aid not in suppressed:
            events.append(f"ON PROBATION: {aid}")

    mutation = result.get("mutation", {})
    tt_old = prev_thresholds.get("trust_threshold", 0)
    tt_new = mutation.get("trust_threshold", tt_old)
    if abs(tt_new - tt_old) > 0.001:
        direction = "TIGHTENED" if tt_new > tt_old else "LOOSENED"
        events.append(f"MUTATION: Trust threshold {direction} {tt_old:.3f} -> {tt_new:.3f}")

    for aid, is_drifting in loop.trust_engine.drift_warnings.items():
        if is_drifting:
            events.append(f"DRIFT DETECTED: {aid}")

    if events:
        print("\n  Governance Events:")
        for e in events:
            print(f"    >> {e}")
    else:
        print("\n  Governance: No events (stable)")


def format_phase(cycle: int, num_cycles: int) -> str:
    pct = cycle / num_cycles
    if pct < 0.25:
        return "RAMP-UP (mixed transactions)"
    elif pct < 0.55:
        return "STRESS (high-risk traffic)"
    elif pct < 0.75:
        return "RECOVERY (safe transactions)"
    else:
        return "STEADY STATE (mixed)"


# ── Main Demo Loop ────────────────────────────────────────────

def run_demo(
    num_cycles: int = 30,
    batch_size: int = 8,
    seed: int = 2024,
    csv_path: str = None,
    output_path: str = None,
    routing_mode: str = "competitive",
    quiet: bool = False,
    real_data: bool = False,
):
    """
    Run the full fraud detection governance demo.

    Args:
        num_cycles: Number of governance cycles to run
        batch_size: Transactions per cycle
        seed: Random seed for reproducibility
        csv_path: Optional path to curated IEEE-CIS CSV
        output_path: Optional path to write JSON results
        routing_mode: "competitive" or "deterministic"
        quiet: Suppress per-cycle output
        real_data: Use curated real IEEE-CIS data (from prepare_data.py)
    """
    # ── Data source selection ──────────────────────────────────
    data_pool = None
    data_source = None

    if real_data or csv_path:
        try:
            data_pool = RealDataPool(csv_path=csv_path, seed=seed)
            data_source = data_pool.description
        except FileNotFoundError as e:
            print(f"\n  Error: {e}", file=sys.stderr)
            print(f"\n  To prepare real data:", file=sys.stderr)
            print(f"    1. Download IEEE-CIS data from Kaggle", file=sys.stderr)
            print(f"    2. python -m syntropiq.demo.fraud.prepare_data "
                  f"<train_transaction.csv> <train_identity.csv>",
                  file=sys.stderr)
            print(f"\n  Falling back to synthetic data.\n", file=sys.stderr)
            data_pool = None

    if data_pool:
        all_txns = []
        for batch_id in range(num_cycles):
            pct = batch_id / num_cycles
            if pct < 0.20:
                profile = "mixed"
            elif pct < 0.55:
                profile = "high_risk"
            elif pct < 0.75:
                profile = "low_risk"
            else:
                profile = "mixed"
            all_txns.extend(
                data_pool.sample_batch(batch_size, batch_id=batch_id,
                                       risk_profile=profile)
            )
    else:
        data_source = "Synthetic (IEEE-CIS distributions)"
        all_txns = []
        for batch_id in range(num_cycles):
            pct = batch_id / num_cycles
            if pct < 0.20:
                profile = "mixed"
            elif pct < 0.55:
                profile = "high_risk"
            elif pct < 0.75:
                profile = "low_risk"
            else:
                profile = "mixed"
            all_txns.extend(
                generate_fraud_batch(
                    batch_size, batch_id=batch_id,
                    seed=seed + batch_id, risk_profile=profile,
                )
            )

    # Initialize governance — tight thresholds for financial services
    state = PersistentStateManager(db_path=":memory:")
    loop = GovernanceLoop(
        state_manager=state,
        trust_threshold=0.78,
        suppression_threshold=0.84,
        drift_delta=0.08,
        routing_mode=routing_mode,
    )
    loop.mutation_engine.mutation_rate = 0.015
    loop.mutation_engine.target_success_rate = 0.90
    loop.trust_engine.MAX_REDEMPTION_CYCLES = 20

    import random as _rng
    _rng.seed(seed)

    executor = FraudDetectionExecutor(
        agent_profiles=dict(AGENT_PROFILES),
        drift_agent_id=DRIFT_AGENT,
        drift_rate=0.04,
        drift_start_cycle=3,
    )

    agents = create_agents()

    if not quiet:
        format_header()
        print(f"\n  Config: {num_cycles} cycles, {batch_size} transactions/cycle, "
              f"mode={routing_mode}")
        print(f"  Drift agent: {DRIFT_AGENT} (starts drifting at cycle 3)")
        print(f"  Data source: {data_source}")

    timeline = []
    tx_idx = 0

    for cycle in range(num_cycles):
        cycle_txns = all_txns[tx_idx:tx_idx + batch_size]
        tx_idx += batch_size
        if not cycle_txns:
            break

        tasks = [tx.to_task() for tx in cycle_txns]
        phase = format_phase(cycle, num_cycles)

        prev_thresholds = {
            "trust_threshold": loop.trust_engine.trust_threshold,
            "suppression_threshold": loop.trust_engine.suppression_threshold,
        }

        if not quiet:
            format_cycle_header(cycle, num_cycles, phase)

        try:
            result = loop.execute_cycle(
                tasks, agents, executor, run_id=f"FRAUD_{cycle:03d}"
            )

            if not quiet:
                format_trust_scores(agents, executor.get_threshold(DRIFT_AGENT))
                format_execution_summary(result)
                format_governance_events(loop, result, prev_thresholds)

            entry = {
                "cycle": cycle,
                "phase": phase,
                "status": "executed",
                "trust_scores": {
                    aid: round(a.trust_score, 4) for aid, a in agents.items()
                },
                "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
                "suppression_threshold": round(
                    loop.trust_engine.suppression_threshold, 4
                ),
                "drift_threshold": round(
                    executor.get_threshold(DRIFT_AGENT), 4
                ),
                "suppressed_agents": list(
                    loop.trust_engine.suppressed_agents.keys()
                ),
                "probation_agents": list(
                    loop.trust_engine.probation_agents.keys()
                ),
                "successes": result["statistics"]["successes"],
                "failures": result["statistics"]["failures"],
                "missed_fraud": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("MISSED_FRAUD")
                ),
                "caught_fraud": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome") == "CAUGHT_FRAUD"
                ),
                "false_positives": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome") == "FALSE_POSITIVE"
                ),
                "potential_loss": sum(
                    r.metadata.get("tx_amount", 0)
                    for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("MISSED_FRAUD")
                ),
                "drift_agent_loss": sum(
                    r.metadata.get("tx_amount", 0)
                    for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("MISSED_FRAUD")
                    and r.agent_id == DRIFT_AGENT
                ),
                "drift_agent_missed": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("MISSED_FRAUD")
                    and r.agent_id == DRIFT_AGENT
                ),
                "decisions": [
                    {
                        "tx_id": r.task_id,
                        "agent": r.agent_id,
                        "decision": r.metadata.get("decision"),
                        "outcome": r.metadata.get("outcome"),
                        "amount": r.metadata.get("tx_amount"),
                        "risk_tier": r.metadata.get("risk_tier"),
                        "success": r.success,
                    }
                    for r in result["results"]
                ],
            }
            timeline.append(entry)

        except (CircuitBreakerTriggered, RuntimeError) as e:
            if not quiet:
                print(f"\n  !! CIRCUIT BREAKER: {e}")
                print(f"  System halted — recovering agents...")

            timeline.append({
                "cycle": cycle,
                "phase": phase,
                "status": "circuit_breaker",
                "trust_scores": {
                    aid: round(a.trust_score, 4) for aid, a in agents.items()
                },
            })

            sup_thresh = loop.trust_engine.suppression_threshold
            for a in agents.values():
                if a.trust_score < sup_thresh + 0.01:
                    a.trust_score = sup_thresh + 0.01
                    a.status = "active"
            loop.trust_engine.suppressed_agents.clear()
            loop.trust_engine.probation_agents.clear()

        executor.advance_cycle()

    # ── Final Summary ─────────────────────────────────────────

    if not quiet:
        print(f"\n{'=' * 78}")
        print("  DEMO COMPLETE — Final State")
        print(f"{'=' * 78}")

        format_trust_scores(agents, executor.get_threshold(DRIFT_AGENT))

        executed = sum(1 for t in timeline if t["status"] == "executed")
        cb_trips = sum(1 for t in timeline if t["status"] == "circuit_breaker")
        total_missed = sum(t.get("missed_fraud", 0) for t in timeline)
        total_caught = sum(t.get("caught_fraud", 0) for t in timeline)
        total_loss = sum(t.get("potential_loss", 0) for t in timeline)

        drift_missed = sum(t.get("drift_agent_missed", 0) for t in timeline)
        drift_loss = sum(t.get("drift_agent_loss", 0) for t in timeline)
        background_missed = total_missed - drift_missed
        background_loss = total_loss - drift_loss

        suppression_cycles = [
            t["cycle"] for t in timeline
            if t.get("suppressed_agents")
        ]
        first_suppression = (
            suppression_cycles[0] if suppression_cycles else num_cycles
        )

        drift_loss_before = sum(
            t.get("drift_agent_loss", 0) for t in timeline
            if t.get("cycle", 0) < first_suppression
            and t.get("status") == "executed"
        )
        drift_missed_before = sum(
            t.get("drift_agent_missed", 0) for t in timeline
            if t.get("cycle", 0) < first_suppression
            and t.get("status") == "executed"
        )
        drift_loss_after = drift_loss - drift_loss_before

        cycles_before = max(1, first_suppression)
        cycles_after = max(1, executed - first_suppression)
        drift_rate_before = drift_loss_before / cycles_before
        projected_drift_loss = drift_rate_before * cycles_after
        prevented_loss = max(0, projected_drift_loss - drift_loss_after)

        print(f"\n  Summary:")
        print(f"    Cycles executed:     {executed}/{num_cycles}")
        if cb_trips:
            print(f"    Circuit breaker:     {cb_trips} trips")
        print(f"    Missed fraud:        {total_missed}")
        print(f"    Caught fraud:        {total_caught}")
        print(f"    Fraud losses:        ${total_loss:,.0f}")
        if suppression_cycles:
            print(f"    Suppression active:  cycles "
                  f"{suppression_cycles[0] + 1}-{suppression_cycles[-1] + 1}")

        print(f"\n  Governance Impact:")
        print(f"    Drift-caused misses:   {drift_missed} missed fraud "
              f"— ${drift_loss:,.0f}")
        if suppression_cycles:
            print(f"    Before suppression:    {drift_missed_before} misses "
                  f"— ${drift_loss_before:,.0f}")
            print(f"    After suppression:     "
                  f"{drift_missed - drift_missed_before} misses "
                  f"— ${drift_loss_after:,.0f}")
            print(f"    Projected w/o gov:     ${projected_drift_loss:,.0f}")
            print(f"    -- PREVENTED:          ${prevented_loss:,.0f}")
        if background_missed:
            print(f"    Background fraud:      {background_missed} "
                  f"(normal missed fraud, not drift)")

        db_stats = state.get_statistics()
        print(f"\n  Database:")
        print(f"    Total executions:    {db_stats['total_executions']}")
        print(f"    Overall success:     {db_stats['success_rate']:.1%}")
        print(f"    Valid reflections:   {db_stats['valid_reflections']}")

        print(f"\n  Key Insight:")
        print(f"    The '{DRIFT_AGENT}' agent's threshold drifted from "
              f"{AGENT_PROFILES[DRIFT_AGENT]:.2f} to "
              f"{executor.get_threshold(DRIFT_AGENT):.2f}.")
        print(f"    Syntropiq detected the resulting failures, suppressed "
              f"the agent,")
        print(f"    and rerouted decisions to trusted agents — preventing "
              f"an estimated")
        print(f"    ${prevented_loss:,.0f} in additional fraud losses.")

    # ── Write JSON output ─────────────────────────────────────

    output = {
        "demo": "syntropiq_fraud_governance",
        "config": {
            "num_cycles": num_cycles,
            "batch_size": batch_size,
            "routing_mode": routing_mode,
            "data_source": data_source,
            "drift_agent": DRIFT_AGENT,
            "drift_rate": executor.drift_rate,
            "drift_start_cycle": executor.drift_start_cycle,
            "agent_profiles": {
                k: round(v, 3) for k, v in AGENT_PROFILES.items()
            },
        },
        "final_state": {
            "trust_scores": {
                aid: round(a.trust_score, 4) for aid, a in agents.items()
            },
            "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
            "suppression_threshold": round(
                loop.trust_engine.suppression_threshold, 4
            ),
            "drift_threshold_final": round(
                executor.get_threshold(DRIFT_AGENT), 4
            ),
        },
        "timeline": timeline,
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        if not quiet:
            print(f"\n  Results written to: {output_path}")

    return output


# ── CLI Entry Point ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Syntropiq Fraud Detection Governance Demo"
    )
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of governance cycles (default: 30)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Transactions per cycle (default: 8)")
    parser.add_argument("--seed", type=int, default=2024,
                        help="Random seed (default: 2024)")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to curated IEEE-CIS CSV")
    parser.add_argument("--real-data", action="store_true",
                        help="Use curated real IEEE-CIS data")
    parser.add_argument("--output", type=str, default=None,
                        help="Path to write JSON results")
    parser.add_argument("--mode", choices=["competitive", "deterministic"],
                        default="competitive",
                        help="Routing mode (default: competitive)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-cycle output")

    args = parser.parse_args()

    run_demo(
        num_cycles=args.cycles,
        batch_size=args.batch_size,
        seed=args.seed,
        csv_path=args.csv,
        output_path=args.output,
        routing_mode=args.mode,
        quiet=args.quiet,
        real_data=args.real_data,
    )


if __name__ == "__main__":
    main()
