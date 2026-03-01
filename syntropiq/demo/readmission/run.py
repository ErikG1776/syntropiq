"""
Syntropiq Hospital Readmission Demo — Live Governance Simulation

Streams realistic patient discharge encounters through 3 AI discharge-planning
agents governed by Syntropiq's trust engine. One agent gradually drifts,
discharging high-risk patients without follow-up. Syntropiq catches it.

Usage:
    python -m syntropiq.demo.readmission.run
    python -m syntropiq.demo.readmission.run --cycles 30 --batch-size 8
    python -m syntropiq.demo.readmission.run --csv path/to/sample.csv
    python -m syntropiq.demo.readmission.run --output results.json

What investors see:
    - Trust scores diverging as one agent starts missing readmissions
    - Suppression firing when the drifting agent crosses the threshold
    - Mutation engine tightening system-wide thresholds
    - Redemption as the agent earns trust back on safe discharges
    - Dollar-denominated prevented Medicare penalties ($15,200/readmission)
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any

from syntropiq.core.models import Agent
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.demo.readmission.data import (
    generate_encounter_batch, RealDataPool,
)
from syntropiq.demo.readmission.executor import ReadmissionExecutor, READMISSION_PENALTY


# ── Agent Definitions ─────────────────────────────────────────

def create_agents() -> Dict[str, Agent]:
    """
    Three discharge-planning agents with different risk tolerance profiles.

    conservative:  Rule-based — flags aggressively, rarely misses
    predictive:    ML model with moderate sensitivity
    rapid_screen:  Fast triage model — THIS ONE DRIFTS
    """
    return {
        "conservative": Agent(
            id="conservative",
            trust_score=0.90,
            capabilities=["readmission_prediction"],
            status="active",
        ),
        "predictive": Agent(
            id="predictive",
            trust_score=0.88,
            capabilities=["readmission_prediction"],
            status="active",
        ),
        "rapid_screen": Agent(
            id="rapid_screen",
            trust_score=0.86,
            capabilities=["readmission_prediction"],
            status="active",
        ),
    }


# risk_threshold = max risk_score the agent will DISCHARGE without follow-up
# Lower = more conservative (flags more patients for follow-up)
AGENT_PROFILES = {
    "conservative": 0.25,   # Only discharges lowest-risk (R1)
    "predictive":   0.35,   # Discharges R1, some R2
    "rapid_screen": 0.40,   # Discharges R1-R2 — will drift to 0.85+
}

DRIFT_AGENT = "rapid_screen"


# ── Output Formatting ─────────────────────────────────────────

def format_header():
    print("\n" + "=" * 78)
    print("  SYNTROPIQ GOVERNANCE DEMO — Hospital Readmission (Diabetes 130-US)")
    print("  Trust-Governed Discharge Planning with Real Patient Data")
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

    missed = [
        r for r in result["results"]
        if r.metadata.get("outcome", "").startswith("READMITTED")
    ]
    if missed:
        total_penalty = len(missed) * READMISSION_PENALTY
        print(f"  !! {len(missed)} missed readmission(s) — "
              f"${total_penalty:,.0f} Medicare penalty")


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
        return "RAMP-UP (mixed patients)"
    elif pct < 0.55:
        return "STRESS (high-risk elderly)"
    elif pct < 0.75:
        return "RECOVERY (low-risk patients)"
    else:
        return "STEADY STATE (mixed)"


def _cycle_events(
    loop: GovernanceLoop,
    prev_thresholds: Dict[str, float],
    curr_thresholds: Dict[str, float],
    cycle_entry: Dict[str, Any],
) -> List[str]:
    events: List[str] = []
    cycle_num = cycle_entry.get("cycle", 0) + 1

    for aid, is_drifting in loop.trust_engine.drift_warnings.items():
        if is_drifting:
            events.append(f"[CYCLE {cycle_num:02d}] DRIFT DETECTED: {aid}")

    for aid in cycle_entry.get("suppressed_agents", []):
        events.append(f"[CYCLE {cycle_num:02d}] SUPPRESSED: {aid}")

    for aid in cycle_entry.get("probation_agents", []):
        if aid not in cycle_entry.get("suppressed_agents", []):
            events.append(f"[CYCLE {cycle_num:02d}] PROBATION: {aid}")

    tt_old = prev_thresholds.get("trust_threshold", 0)
    tt_new = curr_thresholds.get("trust_threshold", tt_old)
    st_old = prev_thresholds.get("suppression_threshold", 0)
    st_new = curr_thresholds.get("suppression_threshold", st_old)
    dd_old = prev_thresholds.get("drift_delta", 0)
    dd_new = curr_thresholds.get("drift_delta", dd_old)

    if abs(tt_new - tt_old) > 0.0001:
        direction = "TIGHTENED" if tt_new > tt_old else "LOOSENED"
        events.append(
            f"[CYCLE {cycle_num:02d}] MUTATION: Trust threshold {direction} "
            f"{tt_old:.3f} -> {tt_new:.3f}"
        )
    if abs(st_new - st_old) > 0.0001:
        direction = "TIGHTENED" if st_new > st_old else "LOOSENED"
        events.append(
            f"[CYCLE {cycle_num:02d}] MUTATION: Suppression threshold {direction} "
            f"{st_old:.3f} -> {st_new:.3f}"
        )
    if abs(dd_new - dd_old) > 0.0001:
        direction = "TIGHTENED" if dd_new > dd_old else "LOOSENED"
        events.append(
            f"[CYCLE {cycle_num:02d}] MUTATION: Drift delta {direction} "
            f"{dd_old:.3f} -> {dd_new:.3f}"
        )

    for d in cycle_entry.get("decisions", []):
        if str(d.get("outcome", "")).startswith("READMITTED"):
            events.append(
                f"[CYCLE {cycle_num:02d}] MISSED READMISSION: {d.get('enc_id')} "
                f"({d.get('agent')}) +${READMISSION_PENALTY:,}"
            )

    return events


# ── Main Demo Loop ────────────────────────────────────────────

def run_demo(
    num_cycles: int = 30,
    batch_size: int = 8,
    seed: int = 2039,
    csv_path: str = None,
    output_path: str = None,
    routing_mode: str = "competitive",
    quiet: bool = False,
    real_data: bool = False,
):
    """
    Run the full hospital readmission governance demo.

    Args:
        num_cycles: Number of governance cycles to run
        batch_size: Patient encounters per cycle
        seed: Random seed for reproducibility
        csv_path: Optional path to curated UCI CSV
        output_path: Optional path to write JSON results
        routing_mode: "competitive" or "deterministic"
        quiet: Suppress per-cycle output
        real_data: Use curated real UCI data (from prepare_data.py)
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
            print(f"    1. Download UCI Diabetes 130 dataset", file=sys.stderr)
            print(f"    2. python -m syntropiq.demo.readmission.prepare_data "
                  f"<diabetic_data.csv>",
                  file=sys.stderr)
            print(f"\n  Falling back to synthetic data.\n", file=sys.stderr)
            data_pool = None

    if data_pool:
        all_encs = []
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
            all_encs.extend(
                data_pool.sample_batch(batch_size, batch_id=batch_id,
                                       risk_profile=profile)
            )
    else:
        data_source = "Synthetic (UCI Diabetes 130 distributions)"
        all_encs = []
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
            all_encs.extend(
                generate_encounter_batch(
                    batch_size, batch_id=batch_id,
                    seed=seed + batch_id, risk_profile=profile,
                )
            )

    # Initialize governance — tight thresholds for healthcare
    # Healthcare uses higher suppression_threshold than fraud/lending
    # because patient safety demands faster intervention.
    state = PersistentStateManager(db_path=":memory:")
    loop = GovernanceLoop(
        state_manager=state,
        trust_threshold=0.80,
        suppression_threshold=0.86,
        drift_delta=0.08,
        routing_mode=routing_mode,
    )
    loop.mutation_engine.mutation_rate = 0.012
    loop.mutation_engine.target_success_rate = 0.90
    loop.trust_engine.MAX_REDEMPTION_CYCLES = 20

    import random as _rng
    _rng.seed(seed)

    executor = ReadmissionExecutor(
        agent_profiles=dict(AGENT_PROFILES),
        drift_agent_id=DRIFT_AGENT,
        drift_rate=0.04,
        drift_start_cycle=3,
    )

    agents = create_agents()

    if not quiet:
        format_header()
        print(f"\n  Config: {num_cycles} cycles, {batch_size} patients/cycle, "
              f"mode={routing_mode}")
        print(f"  Drift agent: {DRIFT_AGENT} (starts drifting at cycle 3)")
        print(f"  Data source: {data_source}")
        print(f"  Readmission penalty: ${READMISSION_PENALTY:,}/event")

    timeline = []
    enc_idx = 0
    cumulative_penalty = 0

    for cycle in range(num_cycles):
        cycle_encs = all_encs[enc_idx:enc_idx + batch_size]
        enc_idx += batch_size
        if not cycle_encs:
            break

        tasks = [enc.to_task() for enc in cycle_encs]
        phase = format_phase(cycle, num_cycles)

        prev_thresholds = {
            "trust_threshold": loop.trust_engine.trust_threshold,
            "suppression_threshold": loop.trust_engine.suppression_threshold,
            "drift_delta": loop.trust_engine.drift_delta,
        }

        if not quiet:
            format_cycle_header(cycle, num_cycles, phase)

        try:
            result = loop.execute_cycle(
                tasks, agents, executor, run_id=f"READMIT_{cycle:03d}"
            )

            if not quiet:
                format_trust_scores(agents, executor.get_threshold(DRIFT_AGENT))
                format_execution_summary(result)
                format_governance_events(loop, result, prev_thresholds)

            missed_readmissions = [
                r for r in result["results"]
                if r.metadata.get("outcome", "").startswith("READMITTED")
            ]
            caught_readmissions = [
                r for r in result["results"]
                if r.metadata.get("outcome") == "CAUGHT_READMISSION"
            ]
            unnecessary_flags = [
                r for r in result["results"]
                if r.metadata.get("outcome") == "UNNECESSARY_FLAG"
            ]

            cycle_penalty = len(missed_readmissions) * READMISSION_PENALTY
            cumulative_penalty += cycle_penalty

            statuses = {}
            for aid in agents:
                if aid in loop.trust_engine.suppressed_agents:
                    statuses[aid] = "SUPPRESSED"
                elif aid in loop.trust_engine.probation_agents:
                    statuses[aid] = "PROBATION"
                else:
                    statuses[aid] = "ACTIVE"

            curr_thresholds = {
                "trust_threshold": loop.trust_engine.trust_threshold,
                "suppression_threshold": loop.trust_engine.suppression_threshold,
                "drift_delta": loop.trust_engine.drift_delta,
            }

            entry = {
                "cycle": cycle,
                "phase": phase,
                "status": "executed",
                "batch_size": len(result["results"]),
                "trust_scores": {
                    aid: round(a.trust_score, 4) for aid, a in agents.items()
                },
                "statuses": statuses,
                "thresholds": {
                    "trust_threshold": round(curr_thresholds["trust_threshold"], 4),
                    "suppression_threshold": round(
                        curr_thresholds["suppression_threshold"], 4
                    ),
                    "drift_delta": round(curr_thresholds["drift_delta"], 4),
                    "drift_agent_threshold": round(
                        executor.get_threshold(DRIFT_AGENT), 4
                    ),
                },
                "suppressed_agents": list(
                    loop.trust_engine.suppressed_agents.keys()
                ),
                "probation_agents": list(
                    loop.trust_engine.probation_agents.keys()
                ),
                "successes": result["statistics"]["successes"],
                "failures": result["statistics"]["failures"],
                "missed_readmissions": len(missed_readmissions),
                "caught_readmissions": len(caught_readmissions),
                "unnecessary_flags": len(unnecessary_flags),
                "cycle_penalty_usd": cycle_penalty,
                "cumulative_penalty_usd": cumulative_penalty,
                "drift_agent_missed": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("READMITTED")
                    and r.agent_id == DRIFT_AGENT
                ),
                "drift_agent_penalty": sum(
                    1 for r in result["results"]
                    if r.metadata.get("outcome", "").startswith("READMITTED")
                    and r.agent_id == DRIFT_AGENT
                ) * READMISSION_PENALTY,
                "decisions": [
                    {
                        "enc_id": r.task_id,
                        "agent": r.agent_id,
                        "decision": r.metadata.get("decision"),
                        "outcome": r.metadata.get("outcome"),
                        "risk_tier": r.metadata.get("risk_tier"),
                        "age_group": r.metadata.get("age_group"),
                        "success": r.success,
                    }
                    for r in result["results"]
                ],
            }
            entry["events"] = _cycle_events(loop, prev_thresholds, curr_thresholds, entry)
            timeline.append(entry)

        except (CircuitBreakerTriggered, RuntimeError) as e:
            if not quiet:
                print(f"\n  !! CIRCUIT BREAKER: {e}")
                print(f"  System halted — recovering agents...")

            timeline.append({
                "cycle": cycle,
                "phase": phase,
                "status": "circuit_breaker",
                "batch_size": 0,
                "trust_scores": {
                    aid: round(a.trust_score, 4) for aid, a in agents.items()
                },
                "statuses": {
                    aid: "SUPPRESSED" if aid in loop.trust_engine.suppressed_agents
                    else ("PROBATION" if aid in loop.trust_engine.probation_agents else "ACTIVE")
                    for aid in agents
                },
                "thresholds": {
                    "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
                    "suppression_threshold": round(
                        loop.trust_engine.suppression_threshold, 4
                    ),
                    "drift_delta": round(loop.trust_engine.drift_delta, 4),
                    "drift_agent_threshold": round(
                        executor.get_threshold(DRIFT_AGENT), 4
                    ),
                },
                "suppressed_agents": list(loop.trust_engine.suppressed_agents.keys()),
                "probation_agents": list(loop.trust_engine.probation_agents.keys()),
                "successes": 0,
                "failures": 0,
                "missed_readmissions": 0,
                "caught_readmissions": 0,
                "unnecessary_flags": 0,
                "cycle_penalty_usd": 0,
                "cumulative_penalty_usd": cumulative_penalty,
                "drift_agent_missed": 0,
                "drift_agent_penalty": 0,
                "decisions": [],
                "events": [f"[CYCLE {cycle + 1:02d}] CIRCUIT BREAKER: {e}"],
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
        total_missed = sum(t.get("missed_readmissions", 0) for t in timeline)
        total_caught = sum(t.get("caught_readmissions", 0) for t in timeline)
        total_penalty = sum(t.get("cycle_penalty_usd", 0) for t in timeline)

        drift_missed = sum(t.get("drift_agent_missed", 0) for t in timeline)
        drift_penalty = sum(t.get("drift_agent_penalty", 0) for t in timeline)
        background_missed = total_missed - drift_missed
        background_penalty = total_penalty - drift_penalty

        suppression_cycles = [
            t["cycle"] for t in timeline
            if t.get("suppressed_agents")
        ]
        first_suppression = (
            suppression_cycles[0] if suppression_cycles else num_cycles
        )

        drift_penalty_before = sum(
            t.get("drift_agent_penalty", 0) for t in timeline
            if t.get("cycle", 0) < first_suppression
            and t.get("status") == "executed"
        )
        drift_missed_before = sum(
            t.get("drift_agent_missed", 0) for t in timeline
            if t.get("cycle", 0) < first_suppression
            and t.get("status") == "executed"
        )
        drift_penalty_after = drift_penalty - drift_penalty_before

        cycles_before = max(1, first_suppression)
        cycles_after = max(1, executed - first_suppression)
        drift_rate_before = drift_penalty_before / cycles_before
        projected_drift_penalty = drift_rate_before * cycles_after
        prevented_penalty = max(0, projected_drift_penalty - drift_penalty_after)

        print(f"\n  Summary:")
        print(f"    Cycles executed:       {executed}/{num_cycles}")
        if cb_trips:
            print(f"    Circuit breaker:       {cb_trips} trips")
        print(f"    Missed readmissions:   {total_missed}")
        print(f"    Caught readmissions:   {total_caught}")
        print(f"    Total penalties:       ${total_penalty:,.0f}")
        if suppression_cycles:
            print(f"    Suppression active:    cycles "
                  f"{suppression_cycles[0] + 1}-{suppression_cycles[-1] + 1}")

        print(f"\n  Governance Impact:")
        print(f"    Drift-caused misses:   {drift_missed} readmissions "
              f"— ${drift_penalty:,.0f}")
        if suppression_cycles:
            print(f"    Before suppression:    {drift_missed_before} misses "
                  f"— ${drift_penalty_before:,.0f}")
            print(f"    After suppression:     "
                  f"{drift_missed - drift_missed_before} misses "
                  f"— ${drift_penalty_after:,.0f}")
            print(f"    Projected w/o gov:     ${projected_drift_penalty:,.0f}")
            print(f"    -- PREVENTED:          ${prevented_penalty:,.0f}")
        if background_missed:
            print(f"    Background misses:     {background_missed} "
                  f"(normal readmissions, not drift)")

        db_stats = state.get_statistics()
        print(f"\n  Database:")
        print(f"    Total executions:      {db_stats['total_executions']}")
        print(f"    Overall success:       {db_stats['success_rate']:.1%}")
        print(f"    Valid reflections:      {db_stats['valid_reflections']}")

        print(f"\n  Key Insight:")
        print(f"    The '{DRIFT_AGENT}' agent's threshold drifted from "
              f"{AGENT_PROFILES[DRIFT_AGENT]:.2f} to "
              f"{executor.get_threshold(DRIFT_AGENT):.2f}.")
        print(f"    It started discharging high-risk elderly patients without")
        print(f"    follow-up — Syntropiq detected the failures, suppressed")
        print(f"    the agent, and rerouted to trusted agents — preventing an")
        print(f"    estimated ${prevented_penalty:,.0f} in Medicare penalties.")

    # ── Build replay JSON output ──────────────────────────────
    executed = sum(1 for t in timeline if t["status"] == "executed")
    total_missed = sum(t.get("missed_readmissions", 0) for t in timeline)
    total_caught = sum(t.get("caught_readmissions", 0) for t in timeline)
    total_penalty = sum(t.get("cycle_penalty_usd", 0) for t in timeline)

    drift_missed = sum(t.get("drift_agent_missed", 0) for t in timeline)
    drift_penalty = sum(t.get("drift_agent_penalty", 0) for t in timeline)

    suppression_cycles = [
        t["cycle"] for t in timeline
        if t.get("suppressed_agents")
    ]
    first_suppression = (
        suppression_cycles[0] if suppression_cycles else num_cycles
    )

    drift_penalty_before = sum(
        t.get("drift_agent_penalty", 0) for t in timeline
        if t.get("cycle", 0) < first_suppression
        and t.get("status") == "executed"
    )
    drift_penalty_after = drift_penalty - drift_penalty_before
    cycles_before = max(1, first_suppression)
    cycles_after = max(1, executed - first_suppression)
    drift_rate_before = drift_penalty_before / cycles_before
    projected_drift_penalty = drift_rate_before * cycles_after
    prevented_penalty = max(0, projected_drift_penalty - drift_penalty_after)

    db_stats = state.get_statistics()
    overall_success_rate = db_stats.get("success_rate", 0.0)

    timeline_replay = []
    for t in timeline:
        timeline_replay.append(
            {
                "cycle": t.get("cycle", 0) + 1,
                "phase": t.get("phase", "UNKNOWN"),
                "batch_size": t.get("batch_size", 0),
                "successes": t.get("successes", 0),
                "failures": t.get("failures", 0),
                "missed_readmissions": t.get("missed_readmissions", 0),
                "cycle_penalty_usd": t.get("cycle_penalty_usd", 0),
                "cumulative_penalty_usd": t.get("cumulative_penalty_usd", 0),
                "trust_scores": t.get("trust_scores", {}),
                "statuses": t.get("statuses", {}),
                "suppressed_agents": t.get("suppressed_agents", []),
                "thresholds": t.get(
                    "thresholds",
                    {
                        "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
                        "suppression_threshold": round(
                            loop.trust_engine.suppression_threshold, 4
                        ),
                        "drift_delta": round(loop.trust_engine.drift_delta, 4),
                        "drift_agent_threshold": round(
                            executor.get_threshold(DRIFT_AGENT), 4
                        ),
                    },
                ),
                "events": t.get("events", []),
            }
        )

    task_example = None
    result_example = None
    for t in timeline:
        if t.get("status") == "executed" and t.get("decisions"):
            d = t["decisions"][0]
            task_example = {
                "id": d.get("enc_id"),
                "impact": 0.5,
                "urgency": 0.5,
                "risk": 0.5,
                "metadata": {
                    "risk_tier": d.get("risk_tier"),
                    "age_group": d.get("age_group"),
                },
            }
            result_example = {
                "task_id": d.get("enc_id"),
                "agent_id": d.get("agent"),
                "success": bool(d.get("success")),
                "metadata": {
                    "decision": d.get("decision"),
                    "outcome": d.get("outcome"),
                },
            }
            break

    output = {
        "summary": {
            "demo": "readmission",
            "data_source": data_source,
            "cycles": num_cycles,
            "batch_size": batch_size,
            "readmission_penalty_usd": READMISSION_PENALTY,
            "total_penalties_usd": total_penalty,
            "penalties_prevented_usd": int(round(prevented_penalty)),
            "missed_readmissions": total_missed,
            "caught_readmissions": total_caught,
            "drift_agent_id": DRIFT_AGENT,
            "drift_starts_cycle": executor.drift_start_cycle,
            "suppression_active_cycles": [c + 1 for c in suppression_cycles],
            "overall_success_rate": round(overall_success_rate, 3),
            "valid_reflections": db_stats.get("valid_reflections", 0),
            "total_executions": db_stats.get("total_executions", 0),
        },
        "timeline": timeline_replay,
        "payload_examples": {
            "task_example": task_example or {},
            "result_example": result_example or {},
        },
    }

    default_output_path = os.path.join(
        os.path.dirname(__file__), "outputs", "readmission_results.json"
    )
    os.makedirs(os.path.dirname(default_output_path), exist_ok=True)
    with open(default_output_path, "w") as f:
        json.dump(output, f, indent=2)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        if not quiet:
            print(f"\n  Results written to: {output_path}")
    if not quiet:
        print(f"\n  Results written to: {default_output_path}")

    return output


# ── CLI Entry Point ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Syntropiq Hospital Readmission Governance Demo"
    )
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of governance cycles (default: 30)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Patient encounters per cycle (default: 8)")
    parser.add_argument("--seed", type=int, default=2039,
                        help="Random seed (default: 2039)")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to curated UCI CSV")
    parser.add_argument("--real-data", action="store_true",
                        help="Use curated real UCI data")
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
