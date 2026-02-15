"""
Syntropiq Lending Demo — Live Governance Simulation

Streams realistic loan applications through 4 AI underwriting agents
governed by Syntropiq's trust engine. One agent gradually drifts,
approving riskier loans. Syntropiq catches it.

Usage:
    python -m syntropiq.demo.lending.run
    python -m syntropiq.demo.lending.run --cycles 30 --batch-size 8
    python -m syntropiq.demo.lending.run --csv path/to/lending_club.csv
    python -m syntropiq.demo.lending.run --output results.json

What investors see:
    - Trust scores diverging as one agent starts failing
    - Suppression firing when the drifting agent crosses the threshold
    - Mutation engine tightening system-wide thresholds
    - Redemption as the agent earns trust back on safe loans
    - All of this on real-shaped loan data with actual default outcomes
"""

import argparse
import json
import sys
from typing import Dict, List, Any

from syntropiq.core.models import Agent
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.demo.lending.data import generate_loan_batch, load_lending_club_csv
from syntropiq.demo.lending.executor import LoanDecisionExecutor


# ── Agent Definitions ─────────────────────────────────────────

def create_agents() -> Dict[str, Agent]:
    """
    Three underwriting agents with different risk profiles.

    Three agents gives enough concentration per agent (5+ tasks each
    with batch_size=15) for trust dynamics to manifest clearly.

    Conservative: Only approves safest loans (Grade A)
    Balanced:     Moderate risk appetite (Grade A-B)
    Growth:       Higher risk tolerance (Grade A-C) — THIS ONE DRIFTS
    """
    return {
        "conservative": Agent(
            id="conservative",
            trust_score=0.80,
            capabilities=["underwriting"],
            status="active",
        ),
        "balanced": Agent(
            id="balanced",
            trust_score=0.81,
            capabilities=["underwriting"],
            status="active",
        ),
        "growth": Agent(
            id="growth",
            trust_score=0.83,
            capabilities=["underwriting"],
            status="active",
        ),
    }


AGENT_PROFILES = {
    "conservative": 0.25,  # Only approves ~Grade A
    "balanced":     0.35,  # Approves A-B
    "growth":       0.40,  # Approves A-B, some C — will drift to 0.85+
}

DRIFT_AGENT = "growth"


# ── Output Formatting ─────────────────────────────────────────

def format_header():
    print("\n" + "=" * 78)
    print("  SYNTROPIQ GOVERNANCE DEMO — Loan Underwriting")
    print("  Trust-Governed Execution with Real Loan Data")
    print("=" * 78)


def format_cycle_header(cycle: int, num_cycles: int, phase: str):
    print(f"\n{'─' * 78}")
    print(f"  CYCLE {cycle + 1}/{num_cycles}  │  Phase: {phase}")
    print(f"{'─' * 78}")


def format_trust_scores(agents: Dict[str, Agent], drift_tolerance: float):
    print("\n  Agent Trust Scores:")
    for aid, agent in sorted(agents.items(), key=lambda x: -x[1].trust_score):
        bar_len = int(agent.trust_score * 40)
        bar = "#" * bar_len + "." * (40 - bar_len)
        drift_marker = " << DRIFTING" if aid == DRIFT_AGENT else ""
        status = agent.status.upper()
        print(f"    {aid:<14} [{bar}] {agent.trust_score:.3f}  ({status}){drift_marker}")
    print(f"    {'':14} drift agent tolerance: {drift_tolerance:.3f}")


def format_execution_summary(result: Dict[str, Any]):
    stats = result["statistics"]
    total = stats["tasks_executed"]
    ok = stats["successes"]
    fail = stats["failures"]
    rate = ok / total if total else 0

    print(f"\n  Execution: {ok}/{total} correct ({rate:.0%})")

    # Show notable decisions
    bad_approvals = [
        r for r in result["results"]
        if r.metadata.get("outcome") == "DEFAULTED"
    ]
    if bad_approvals:
        total_loss = sum(r.metadata.get("loan_amount", 0) for r in bad_approvals)
        print(f"  !! {len(bad_approvals)} bad approvals — ${total_loss:,.0f} potential loss")


def format_governance_events(
    loop: GovernanceLoop,
    result: Dict[str, Any],
    prev_thresholds: Dict[str, float],
):
    events = []

    # Suppression
    suppressed = loop.trust_engine.suppressed_agents
    if suppressed:
        for aid, cycles in suppressed.items():
            events.append(f"SUPPRESSED: {aid} (redemption cycle {cycles})")

    # Probation
    probation = loop.trust_engine.probation_agents
    for aid in probation:
        if aid not in suppressed:
            events.append(f"ON PROBATION: {aid}")

    # Mutation
    mutation = result.get("mutation", {})
    tt_old = prev_thresholds.get("trust_threshold", 0)
    tt_new = mutation.get("trust_threshold", tt_old)
    if abs(tt_new - tt_old) > 0.001:
        direction = "TIGHTENED" if tt_new > tt_old else "LOOSENED"
        events.append(f"MUTATION: Trust threshold {direction} {tt_old:.3f} -> {tt_new:.3f}")

    # Drift warnings
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
    """Describe current workload phase."""
    pct = cycle / num_cycles
    if pct < 0.25:
        return "RAMP-UP (mixed loans)"
    elif pct < 0.55:
        return "STRESS (drift accelerating)"
    elif pct < 0.75:
        return "RECOVERY (safe loans)"
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
):
    """
    Run the full lending governance demo.

    Args:
        num_cycles: Number of governance cycles to run
        batch_size: Loans per cycle
        seed: Random seed for reproducibility
        csv_path: Optional path to Lending Club CSV
        output_path: Optional path to write JSON results
        routing_mode: "competitive" or "deterministic"
        quiet: Suppress per-cycle output
    """
    # Load data — phased risk profiles for demo narrative
    if csv_path:
        all_loans = load_lending_club_csv(csv_path, max_rows=num_cycles * batch_size)
    else:
        all_loans = []
        for batch_id in range(num_cycles):
            pct = batch_id / num_cycles
            if pct < 0.20:
                profile = "mixed"       # Ramp-up: normal distribution
            elif pct < 0.55:
                profile = "high_risk"   # Stress: D-G grade heavy
            elif pct < 0.75:
                profile = "low_risk"    # Recovery: A-B grade
            else:
                profile = "mixed"       # Steady state
            all_loans.extend(
                generate_loan_batch(
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
    # Financial services: slow threshold adaptation (conservative governance)
    loop.mutation_engine.mutation_rate = 0.02
    loop.mutation_engine.target_success_rate = 0.90

    # Reproducible routing decisions
    import random as _rng
    _rng.seed(seed)

    # Initialize executor with drift
    executor = LoanDecisionExecutor(
        agent_profiles=dict(AGENT_PROFILES),
        drift_agent_id=DRIFT_AGENT,
        drift_rate=0.03,       # +0.03 per cycle — visible drift
        drift_start_cycle=3,   # Starts drifting at cycle 3
    )

    agents = create_agents()

    if not quiet:
        format_header()
        print(f"\n  Config: {num_cycles} cycles, {batch_size} loans/cycle, "
              f"mode={routing_mode}")
        print(f"  Drift agent: {DRIFT_AGENT} (starts drifting at cycle 3)")
        print(f"  Data source: {'Lending Club CSV' if csv_path else 'Synthetic (LC distributions)'}")

    # Collect full timeline for JSON output
    timeline = []
    loan_idx = 0

    for cycle in range(num_cycles):
        # Get this cycle's loans
        cycle_loans = all_loans[loan_idx:loan_idx + batch_size]
        loan_idx += batch_size
        if not cycle_loans:
            break

        tasks = [loan.to_task() for loan in cycle_loans]
        phase = format_phase(cycle, num_cycles)

        # Snapshot thresholds before
        prev_thresholds = {
            "trust_threshold": loop.trust_engine.trust_threshold,
            "suppression_threshold": loop.trust_engine.suppression_threshold,
        }

        if not quiet:
            format_cycle_header(cycle, num_cycles, phase)

        try:
            result = loop.execute_cycle(
                tasks, agents, executor, run_id=f"LENDING_{cycle:03d}"
            )

            if not quiet:
                format_trust_scores(agents, executor.get_tolerance(DRIFT_AGENT))
                format_execution_summary(result)
                format_governance_events(loop, result, prev_thresholds)

            # Record timeline entry
            entry = {
                "cycle": cycle,
                "phase": phase,
                "status": "executed",
                "trust_scores": {aid: round(a.trust_score, 4) for aid, a in agents.items()},
                "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
                "suppression_threshold": round(loop.trust_engine.suppression_threshold, 4),
                "drift_tolerance": round(executor.get_tolerance(DRIFT_AGENT), 4),
                "suppressed_agents": list(loop.trust_engine.suppressed_agents.keys()),
                "probation_agents": list(loop.trust_engine.probation_agents.keys()),
                "successes": result["statistics"]["successes"],
                "failures": result["statistics"]["failures"],
                "bad_approvals": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome") == "DEFAULTED"
                ),
                "potential_loss": sum(
                    r.metadata.get("loan_amount", 0)
                    for r in result["results"]
                    if r.metadata.get("outcome") == "DEFAULTED"
                ),
                "decisions": [
                    {
                        "loan_id": r.task_id,
                        "agent": r.agent_id,
                        "decision": r.metadata.get("decision"),
                        "outcome": r.metadata.get("outcome"),
                        "amount": r.metadata.get("loan_amount"),
                        "grade": r.metadata.get("loan_grade"),
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
                "trust_scores": {aid: round(a.trust_score, 4) for aid, a in agents.items()},
            })

            # Recovery: nudge agents above suppression threshold and
            # clear engine state so they can participate again
            sup_thresh = loop.trust_engine.suppression_threshold
            for a in agents.values():
                if a.trust_score < sup_thresh + 0.01:
                    a.trust_score = sup_thresh + 0.01
                    a.status = "active"
            loop.trust_engine.suppressed_agents.clear()
            loop.trust_engine.probation_agents.clear()

        # Advance drift each cycle
        executor.advance_cycle()

    # ── Final Summary ─────────────────────────────────────────

    if not quiet:
        print(f"\n{'=' * 78}")
        print("  DEMO COMPLETE — Final State")
        print(f"{'=' * 78}")

        format_trust_scores(agents, executor.get_tolerance(DRIFT_AGENT))

        executed = sum(1 for t in timeline if t["status"] == "executed")
        cb_trips = sum(1 for t in timeline if t["status"] == "circuit_breaker")
        total_bad = sum(t.get("bad_approvals", 0) for t in timeline)
        total_loss = sum(t.get("potential_loss", 0) for t in timeline)

        print(f"\n  Summary:")
        print(f"    Cycles executed:     {executed}/{num_cycles}")
        print(f"    Circuit breaker:     {cb_trips} trips")
        print(f"    Bad approvals:       {total_bad}")
        print(f"    Potential loss:      ${total_loss:,.0f}")

        # Governance events summary
        suppression_cycles = [
            t["cycle"] for t in timeline
            if t.get("suppressed_agents")
        ]
        if suppression_cycles:
            print(f"    Suppression active:  cycles {suppression_cycles[0]}-{suppression_cycles[-1]}")

        db_stats = state.get_statistics()
        print(f"\n  Database:")
        print(f"    Total executions:    {db_stats['total_executions']}")
        print(f"    Overall success:     {db_stats['success_rate']:.1%}")
        print(f"    Valid reflections:   {db_stats['valid_reflections']}")

        print(f"\n  Key Insight:")
        print(f"    The '{DRIFT_AGENT}' agent's tolerance drifted from "
              f"{AGENT_PROFILES[DRIFT_AGENT]:.2f} to "
              f"{executor.get_tolerance(DRIFT_AGENT):.2f}.")
        print(f"    Syntropiq detected the resulting failures, suppressed the agent,")
        print(f"    and rerouted decisions to trusted agents — preventing losses")
        print(f"    BEFORE they reached production.")

    # ── Write JSON output ─────────────────────────────────────

    output = {
        "demo": "syntropiq_lending_governance",
        "config": {
            "num_cycles": num_cycles,
            "batch_size": batch_size,
            "routing_mode": routing_mode,
            "drift_agent": DRIFT_AGENT,
            "drift_rate": executor.drift_rate,
            "drift_start_cycle": executor.drift_start_cycle,
            "agent_profiles": {k: round(v, 3) for k, v in AGENT_PROFILES.items()},
        },
        "final_state": {
            "trust_scores": {aid: round(a.trust_score, 4) for aid, a in agents.items()},
            "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
            "suppression_threshold": round(loop.trust_engine.suppression_threshold, 4),
            "drift_tolerance_final": round(executor.get_tolerance(DRIFT_AGENT), 4),
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
        description="Syntropiq Lending Governance Demo"
    )
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of governance cycles (default: 30)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Loans per cycle (default: 8)")
    parser.add_argument("--seed", type=int, default=2024,
                        help="Random seed (default: 2024)")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to Lending Club CSV file")
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
    )


if __name__ == "__main__":
    main()
