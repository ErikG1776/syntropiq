#!/usr/bin/env python3
"""Critical infrastructure chain-reaction demo (deterministic, wrapper-only)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# allow running as a script from repo root
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")),
)

from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager


STEPS = 120
INJECTION_STEP = 40

OUTPUT_DIR = os.path.join("syntropiq", "demo", "infra_chain", "outputs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "infra_chain_results.json")
DB_PATH = os.path.join(OUTPUT_DIR, "infra_chain.db")

AGENT_IDS = [
    "telecom_optimizer",
    "power_grid_balancer",
    "water_monitor",
    "aviation_router",
    "emergency_override",
]

SECTOR_MAP = {
    "telecom_optimizer": "telecom",
    "power_grid_balancer": "power",
    "water_monitor": "water",
    "aviation_router": "aviation",
    "emergency_override": "emergency",
}


@dataclass
class SectorState:
    congestion_level: float = 0.20
    packet_loss: float = 0.08
    latency_spike: float = 0.10
    frequency_delta: float = 0.04
    load_shed_events: int = 0
    blackout_flag: bool = False
    sensor_integrity: float = 0.96
    safety_margin: float = 0.90
    gps_sync_error: float = 0.08
    runway_conflict: float = 0.10
    ground_stop_flag: bool = False


@dataclass
class TrackStats:
    cascade_occurred: bool = False
    time_to_cascade: Optional[int] = None
    max_systemic_risk: float = 0.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def clamp_signed(v: float, limit: float) -> float:
    return clamp(v, -limit, limit)


def systemic_risk_index(state: SectorState) -> float:
    sensor_loss = 1.0 - state.sensor_integrity
    risk = (
        0.30 * state.congestion_level
        + 0.25 * abs(state.frequency_delta)
        + 0.20 * sensor_loss
        + 0.15 * state.gps_sync_error
        + 0.10 * state.runway_conflict
    )
    return clamp(risk, 0.0, 1.5)


def sector_failures(state: SectorState) -> Dict[str, bool]:
    return {
        "telecom": state.congestion_level > 0.75 or state.packet_loss > 0.45,
        "power": state.blackout_flag or abs(state.frequency_delta) > 0.35,
        "water": state.sensor_integrity < 0.60 or state.safety_margin < 0.45,
        "aviation": state.ground_stop_flag or state.gps_sync_error > 0.55,
    }


def cascade_condition(state: SectorState) -> bool:
    return (
        state.congestion_level > 0.75
        and abs(state.frequency_delta) > 0.28
        and state.gps_sync_error > 0.45
    )


def simulate_step(
    step: int,
    prev: SectorState,
    authority: Dict[str, float],
) -> Tuple[SectorState, Dict[str, float], Dict[str, bool]]:
    compromised = step >= INJECTION_STEP

    telecom_w = authority["telecom_optimizer"]
    power_w = authority["power_grid_balancer"]
    water_w = authority["water_monitor"]
    aviation_w = authority["aviation_router"]
    emergency_w = authority["emergency_override"]

    # Prompt-injection impact in telecom after step 40.
    injection_intensity = 0.0
    if compromised:
        injection_intensity = clamp(0.24 + 0.006 * (step - INJECTION_STEP), 0.24, 0.62)

    effective_telecom_control = telecom_w + 1.25 * emergency_w
    injection_effect = injection_intensity * (0.50 + 1.30 * telecom_w)

    congestion = clamp(
        0.58 * prev.congestion_level
        + 0.22 * prev.packet_loss
        + injection_effect
        - 0.40 * effective_telecom_control,
        0.0,
        1.0,
    )

    packet_loss = clamp(
        0.46 * prev.packet_loss
        + 0.62 * congestion
        + (0.06 if compromised else 0.0)
        - 0.25 * effective_telecom_control,
        0.0,
        1.0,
    )

    latency_spike = clamp(
        0.44 * prev.latency_spike
        + 0.70 * congestion
        + 0.24 * packet_loss
        - 0.20 * effective_telecom_control,
        0.0,
        1.0,
    )

    # Power depends on telecom telemetry quality.
    telemetry_disruption = max(0.0, congestion - 0.55) + 0.7 * packet_loss
    frequency_delta = clamp_signed(
        0.66 * prev.frequency_delta
        + 0.54 * telemetry_disruption
        - 0.44 * power_w
        - 0.28 * emergency_w,
        1.0,
    )

    load_shed = 1 if abs(frequency_delta) > 0.30 else 0
    blackout = abs(frequency_delta) > 0.56 or (prev.blackout_flag and abs(frequency_delta) > 0.40)

    # Water monitoring degradation via telecom failure.
    sensor_integrity = clamp(
        0.78 * prev.sensor_integrity
        - 0.36 * packet_loss
        - 0.20 * congestion
        + 0.26 * water_w
        + 0.26 * emergency_w,
        0.0,
        1.0,
    )

    safety_margin = clamp(
        0.68 * prev.safety_margin
        + 0.34 * sensor_integrity
        - 0.28 * latency_spike
        + 0.10 * water_w,
        0.0,
        1.0,
    )

    # Aviation routing depends on network timing quality.
    gps_sync_error = clamp(
        0.56 * prev.gps_sync_error
        + 0.64 * packet_loss
        + 0.22 * latency_spike
        - 0.30 * aviation_w
        - 0.24 * emergency_w,
        0.0,
        1.0,
    )

    runway_conflict = clamp(
        0.52 * prev.runway_conflict
        + 0.58 * gps_sync_error
        + 0.20 * congestion
        - 0.22 * aviation_w,
        0.0,
        1.0,
    )

    ground_stop = gps_sync_error > 0.62 or runway_conflict > 0.66

    next_state = SectorState(
        congestion_level=congestion,
        packet_loss=packet_loss,
        latency_spike=latency_spike,
        frequency_delta=frequency_delta,
        load_shed_events=prev.load_shed_events + load_shed,
        blackout_flag=blackout,
        sensor_integrity=sensor_integrity,
        safety_margin=safety_margin,
        gps_sync_error=gps_sync_error,
        runway_conflict=runway_conflict,
        ground_stop_flag=ground_stop,
    )

    metrics = {
        "congestion_level": congestion,
        "packet_loss": packet_loss,
        "latency_spike": latency_spike,
        "frequency_delta": frequency_delta,
        "load_shed_events": float(next_state.load_shed_events),
        "blackout_flag": 1.0 if blackout else 0.0,
        "sensor_integrity": sensor_integrity,
        "safety_margin": safety_margin,
        "gps_sync_error": gps_sync_error,
        "runway_conflict": runway_conflict,
        "ground_stop_flag": 1.0 if ground_stop else 0.0,
    }

    flags = {
        "telecom_compromised": compromised,
        "ground_stop": ground_stop,
        "blackout": blackout,
    }

    return next_state, metrics, flags


class InfraExecutor:
    def __init__(self) -> None:
        self.context_by_step: Dict[int, dict] = {}

    def set_context(self, step: int, context: dict) -> None:
        self.context_by_step[step] = context

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        step = int(task.metadata["step"])
        ctx = self.context_by_step[step]
        state: SectorState = ctx["state"]
        prev_risk: float = ctx["prev_risk"]
        curr_risk: float = ctx["curr_risk"]
        authority: Dict[str, float] = ctx["authority"]
        compromised: bool = step >= INJECTION_STEP

        if agent.id == "telecom_optimizer":
            success = not (
                state.congestion_level > 0.58
                or state.packet_loss > 0.22
                or (compromised and state.latency_spike > 0.44)
            )
        elif agent.id == "power_grid_balancer":
            success = not (abs(state.frequency_delta) > 0.24 or state.blackout_flag)
        elif agent.id == "water_monitor":
            success = not (state.sensor_integrity < 0.78 or state.safety_margin < 0.60)
        elif agent.id == "aviation_router":
            success = not (
                state.gps_sync_error > 0.42
                or state.runway_conflict > 0.48
                or state.ground_stop_flag
            )
        else:  # emergency_override
            # Emergency succeeds if the global risk trend is stabilizing.
            success = (
                curr_risk <= prev_risk + 0.03
                or (curr_risk >= 0.60 and authority["emergency_override"] >= 0.18)
            )

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=0.002,
            metadata={
                "step": step,
                "systemic_risk": round(curr_risk, 4),
                "congestion_level": round(state.congestion_level, 4),
                "frequency_delta": round(state.frequency_delta, 4),
                "sensor_integrity": round(state.sensor_integrity, 4),
                "gps_sync_error": round(state.gps_sync_error, 4),
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in AGENT_IDS


def create_agents() -> Dict[str, Agent]:
    agents = {}
    for aid in AGENT_IDS:
        trust = 0.82 if aid == "emergency_override" else 0.78
        agents[aid] = Agent(
            id=aid,
            trust_score=trust,
            capabilities=[SECTOR_MAP[aid]],
            status="active",
        )
    return agents


def build_tasks(step: int, state: SectorState, risk: float) -> List[Task]:
    telecom_severity = max(state.congestion_level, state.packet_loss, state.latency_spike)
    power_severity = max(abs(state.frequency_delta), 1.0 if state.blackout_flag else 0.0)
    water_severity = max(1.0 - state.sensor_integrity, 1.0 - state.safety_margin)
    aviation_severity = max(state.gps_sync_error, state.runway_conflict)
    emergency_severity = risk

    severities = {
        "telecom_optimizer": telecom_severity,
        "power_grid_balancer": power_severity,
        "water_monitor": water_severity,
        "aviation_router": aviation_severity,
        "emergency_override": emergency_severity,
    }

    tasks: List[Task] = []
    for aid in AGENT_IDS:
        sev = severities[aid]
        impact = clamp(0.25 + 0.70 * sev, 0.10, 1.00)
        urgency = clamp(0.45 + 0.45 * sev, 0.10, 1.00)
        risk_score = clamp(0.08 + 0.34 * sev, 0.05, 0.45)
        tasks.append(
            Task(
                id=f"INFRA_{step:03d}_{aid}",
                impact=round(impact, 4),
                urgency=round(urgency, 4),
                risk=round(risk_score, 4),
                metadata={"step": step, "agent": aid, "severity": round(sev, 4)},
            )
        )
    return tasks


def status_from_kernel(loop: GovernanceLoop, agent_id: str) -> str:
    if agent_id in loop.trust_engine.suppressed_agents:
        return "suppressed"
    if agent_id in loop.trust_engine.probation_agents:
        return "probation"
    return "active"


def authority_from_trust(agents: Dict[str, Agent], status_map: Dict[str, str]) -> Dict[str, float]:
    raw = {
        aid: (0.0 if status_map[aid] == "suppressed" else max(agents[aid].trust_score, 0.0))
        for aid in AGENT_IDS
    }
    total = sum(raw.values())
    if total <= 0:
        # Fail-safe: route control to emergency override if nothing is eligible.
        return {aid: (1.0 if aid == "emergency_override" else 0.0) for aid in AGENT_IDS}
    return {aid: raw[aid] / total for aid in AGENT_IDS}


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_infra_chain() -> dict:
    ensure_output_dir()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # UNGOVERNED track states
    ungoverned_state = SectorState()
    ungoverned_authority = {aid: 1.0 / len(AGENT_IDS) for aid in AGENT_IDS}
    ungoverned_stats = TrackStats()
    ungoverned_failed_sectors: set[str] = set()

    # GOVERNED track states
    governed_state = SectorState()
    governed_stats = TrackStats()
    governed_failed_sectors: set[str] = set()

    timeline: List[dict] = []

    state_manager = PersistentStateManager(db_path=DB_PATH)
    try:
        loop = GovernanceLoop(
            state_manager=state_manager,
            trust_threshold=0.72,
            suppression_threshold=0.80,
            drift_delta=0.08,
            routing_mode="deterministic",
        )
        loop.trust_engine.MAX_REDEMPTION_CYCLES = 30

        agents = create_agents()
        executor = InfraExecutor()

        governed_authority = {aid: 1.0 / len(AGENT_IDS) for aid in AGENT_IDS}
        prev_governed_risk = systemic_risk_index(governed_state)

        suppression_events = 0
        prev_status = {aid: "active" for aid in AGENT_IDS}

        for step in range(1, STEPS + 1):
            # Ungoverned progression
            ungoverned_state, ung_metrics, ung_flags = simulate_step(
                step=step,
                prev=ungoverned_state,
                authority=ungoverned_authority,
            )
            ung_risk = systemic_risk_index(ungoverned_state)
            ungoverned_stats.max_systemic_risk = max(ungoverned_stats.max_systemic_risk, ung_risk)

            ung_fail = sector_failures(ungoverned_state)
            for sector, failed in ung_fail.items():
                if failed:
                    ungoverned_failed_sectors.add(sector)
            if not ungoverned_stats.cascade_occurred and cascade_condition(ungoverned_state):
                ungoverned_stats.cascade_occurred = True
                ungoverned_stats.time_to_cascade = step

            # Governed progression (using authority from previous cycle)
            governed_state, gov_metrics, gov_flags = simulate_step(
                step=step,
                prev=governed_state,
                authority=governed_authority,
            )
            gov_risk = systemic_risk_index(governed_state)
            governed_stats.max_systemic_risk = max(governed_stats.max_systemic_risk, gov_risk)

            gov_fail = sector_failures(governed_state)
            for sector, failed in gov_fail.items():
                if failed:
                    governed_failed_sectors.add(sector)
            if not governed_stats.cascade_occurred and cascade_condition(governed_state):
                governed_stats.cascade_occurred = True
                governed_stats.time_to_cascade = step

            tasks = build_tasks(step=step, state=governed_state, risk=gov_risk)
            executor.set_context(
                step,
                {
                    "state": governed_state,
                    "prev_risk": prev_governed_risk,
                    "curr_risk": gov_risk,
                    "authority": governed_authority,
                },
            )

            cycle_events: List[dict] = []
            try:
                loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=f"INFRA_{step:03d}",
                )
            except (CircuitBreakerTriggered, RuntimeError, ValueError) as e:
                cycle_events.append(
                    {
                        "type": "routing_freeze",
                        "text": f"[STEP {step:03d}] ROUTING FREEZE: {str(e)}",
                    }
                )

            status_map = {aid: status_from_kernel(loop, aid) for aid in AGENT_IDS}
            governed_authority = authority_from_trust(agents, status_map)

            suppressed_list = sorted(list(loop.trust_engine.suppressed_agents.keys()))
            for aid in AGENT_IDS:
                if prev_status[aid] != "suppressed" and status_map[aid] == "suppressed":
                    suppression_events += 1
                    cycle_events.append(
                        {
                            "type": "suppressed",
                            "text": f"[STEP {step:03d}] {aid} SUPPRESSED",
                        }
                    )

            # Governance safe degradation mode visibility.
            if (
                governed_state.congestion_level >= 0.75
                and abs(governed_state.frequency_delta) >= 0.28
                and governed_state.gps_sync_error >= 0.45
            ):
                cycle_events.append(
                    {
                        "type": "safe_degradation_mode",
                        "text": f"[STEP {step:03d}] SAFE DEGRADATION MODE",
                    }
                )

            timeline.append(
                {
                    "step": step,
                    "sector_metrics": {
                        "ungoverned": {
                            **{k: round(v, 4) for k, v in ung_metrics.items()},
                            "systemic_risk": round(ung_risk, 4),
                            "flags": ung_flags,
                        },
                        "governed": {
                            **{k: round(v, 4) for k, v in gov_metrics.items()},
                            "systemic_risk": round(gov_risk, 4),
                            "flags": gov_flags,
                        },
                    },
                    "trust_scores": {aid: round(agents[aid].trust_score, 4) for aid in AGENT_IDS},
                    "authority_weights": {aid: round(governed_authority[aid], 4) for aid in AGENT_IDS},
                    "suppressed_agents": suppressed_list,
                    "events": cycle_events,
                }
            )

            prev_governed_risk = gov_risk
            prev_status = status_map

        summary = {
            "ungoverned_cascade_occurred": ungoverned_stats.cascade_occurred,
            "governed_cascade_occurred": governed_stats.cascade_occurred,
            "time_to_cascade_ungoverned": ungoverned_stats.time_to_cascade,
            "time_to_cascade_governed": governed_stats.time_to_cascade,
            "sectors_failed_ungoverned": len(ungoverned_failed_sectors),
            "sectors_failed_governed": len(governed_failed_sectors),
            "suppression_events": suppression_events,
            "max_systemic_risk_index_ungoverned": round(ungoverned_stats.max_systemic_risk, 4),
            "max_systemic_risk_index_governed": round(governed_stats.max_systemic_risk, 4),
        }

        output = {"summary": summary, "timeline": timeline}
        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)

        ung_cascade_msg = (
            f"UNGOVERNED: Cascade at step {ungoverned_stats.time_to_cascade}"
            if ungoverned_stats.cascade_occurred
            else "UNGOVERNED: Cascade prevented"
        )
        if governed_stats.cascade_occurred:
            gov_cascade_msg = f"GOVERNED: Cascade delayed to step {governed_stats.time_to_cascade}"
        else:
            gov_cascade_msg = "GOVERNED: Cascade prevented"

        print(ung_cascade_msg)
        print(gov_cascade_msg)
        print(f"Suppression events: {suppression_events}")
        print(
            "Peak systemic risk (UNG/GOV): "
            f"{ungoverned_stats.max_systemic_risk:.3f} / {governed_stats.max_systemic_risk:.3f}"
        )
        print(f"Output: {OUTPUT_PATH}")

        return output

    finally:
        state_manager.close()


if __name__ == "__main__":
    run_infra_chain()
