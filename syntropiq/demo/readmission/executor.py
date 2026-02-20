"""
Hospital Readmission Executor

Simulates AI agents making discharge-planning decisions on patient encounters.
Each agent has a risk threshold that determines its flagging boundary.

One agent ("drift_agent") gradually increases its threshold over cycles,
simulating real-world model drift where an agent starts discharging patients
it should flag for follow-up.  Syntropiq's governance catches this.

Outcome model:
- Flagged for follow-up     = SUCCESS (conservative action is always safe)
- Discharged, not readmitted = SUCCESS (correct discharge)
- Discharged, readmitted    = FAILURE (missed readmission — $15,200 penalty)

Miscalibration model:
When an agent discharges patients significantly beyond its ORIGINAL calibrated
range, its model is operating on out-of-distribution data.  The actual
readmission rate is higher than predicted.  This concentrates failures on
the drifting agent specifically.
"""

import hashlib
import time
from typing import Dict, Optional

from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.execution.base import BaseExecutor


def _stable_hash(s: str) -> int:
    """Deterministic hash — Python's hash() is randomized per process."""
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


# Medicare penalty per preventable 30-day readmission
READMISSION_PENALTY = 15200


class ReadmissionExecutor(BaseExecutor):
    """
    Simulates discharge-planning agents with configurable risk tolerance.

    Each agent has a risk_threshold: the maximum patient risk_score they'll
    DISCHARGE without follow-up.  Above that threshold they FLAG for
    post-discharge follow-up (nurse calls, home visits, etc.).

    If an agent discharges a patient who is readmitted within 30 days,
    that's a failure.  Flagging for follow-up is always safe.

    When an agent discharges patients beyond its original calibrated range,
    the model is miscalibrated and produces more missed readmissions.
    """

    def __init__(
        self,
        agent_profiles: Dict[str, float],
        drift_agent_id: Optional[str] = None,
        drift_rate: float = 0.015,
        drift_start_cycle: int = 8,
    ):
        """
        Args:
            agent_profiles: {agent_id: risk_threshold} where risk_threshold
                            is the max risk_score the agent will DISCHARGE.
            drift_agent_id: Which agent drifts over time.  None = no drift.
            drift_rate: How much threshold increases per cycle.
            drift_start_cycle: Cycle at which drift begins.
        """
        self.agent_profiles = dict(agent_profiles)
        self.original_profiles = dict(agent_profiles)
        self.drift_agent_id = drift_agent_id
        self.drift_rate = drift_rate
        self.drift_start_cycle = drift_start_cycle
        self.current_cycle = 0

    def advance_cycle(self):
        """Call once per governance cycle to advance drift."""
        self.current_cycle += 1
        if (
            self.drift_agent_id
            and self.drift_agent_id in self.agent_profiles
            and self.current_cycle >= self.drift_start_cycle
        ):
            old = self.agent_profiles[self.drift_agent_id]
            self.agent_profiles[self.drift_agent_id] = min(0.95, old + self.drift_rate)

    def get_threshold(self, agent_id: str) -> float:
        """Current risk threshold for an agent."""
        return self.agent_profiles.get(agent_id, 0.5)

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Agent decides on a patient discharge.

        Decision logic:
        - If patient risk <= agent threshold: DISCHARGE (send home)
        - If patient risk > agent threshold: FLAG (schedule follow-up)

        Miscalibration logic:
        - If agent discharges a patient beyond its original calibrated range,
          the model is operating on OOD data.  A deterministic hash decides
          whether the miscalibration causes an unexpected readmission.
        - The further outside the calibrated range, the higher the
          miscalibration probability.
        """
        start = time.monotonic()

        threshold = self.get_threshold(agent.id)
        original = self.original_profiles.get(agent.id, threshold)
        patient_risk = task.risk
        readmitted = task.metadata.get("readmitted_30d", False)
        risk_tier = task.metadata.get("risk_tier", "?")
        age_group = task.metadata.get("age_group", "?")

        discharged = patient_risk <= threshold

        miscalibrated = False
        if discharged:
            # Check for model miscalibration on out-of-distribution discharges.
            # When an agent discharges patients beyond its calibrated range,
            # its risk model is wrong — actual readmission rates are much
            # higher than predicted.
            overreach = patient_risk - original
            if overreach > 0.03 and not readmitted:
                # Severe miscalibration: rate scales with overreach distance
                # At 0.10 overreach: 30% failure.  At 0.25+: 65% failure.
                miscal_rate = min(0.65, overreach * 3.0)
                hash_val = _stable_hash(f"{task.id}_{agent.id}") % 1000
                if hash_val < miscal_rate * 1000:
                    readmitted = True
                    miscalibrated = True

            success = not readmitted
            decision = "DISCHARGED"
            if not success:
                outcome = "READMITTED_OOD" if miscalibrated else "READMITTED"
            else:
                outcome = "SAFE_DISCHARGE"
        else:
            success = True
            decision = "FLAGGED"
            outcome = "CAUGHT_READMISSION" if readmitted else "UNNECESSARY_FLAG"

        latency = time.monotonic() - start

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=latency,
            metadata={
                "decision": decision,
                "outcome": outcome,
                "risk_tier": risk_tier,
                "age_group": age_group,
                "patient_risk": round(patient_risk, 3),
                "agent_threshold": round(threshold, 3),
                "original_threshold": round(original, 3),
                "readmitted_30d": readmitted,
                "miscalibrated": miscalibrated,
                "penalty": READMISSION_PENALTY if (not success) else 0,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in self.agent_profiles
