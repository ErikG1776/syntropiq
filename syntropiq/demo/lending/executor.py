"""
Loan Decision Executor

Simulates AI agents making loan approve/deny decisions.
Each agent has a risk tolerance that determines its approval boundary.

One agent ("drift_agent") gradually increases its risk tolerance over
cycles, simulating real-world model drift where an agent starts approving
loans it shouldn't. Syntropiq's governance catches this.

Outcome model (matches how regulators think about it):
- Approved a good loan   = SUCCESS (revenue)
- Approved a defaulted   = FAILURE (loss -- the dangerous outcome)
- Denied any loan        = SUCCESS (conservative action is always safe)

Miscalibration model:
When an agent approves a loan significantly beyond its ORIGINAL calibrated
range, its model is operating on out-of-distribution data. The actual
default rate is higher than the historical average for that grade. This
concentrates failures on the drifting agent specifically.
"""

import time
from typing import Dict, Optional
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.execution.base import BaseExecutor


class LoanDecisionExecutor(BaseExecutor):
    """
    Simulates loan underwriting agents with configurable risk profiles.

    Each agent has a risk_tolerance: the maximum loan risk_score they'll approve.
    If an agent approves a loan that defaults, that's a failure.
    Denials are always safe -- a denial never causes a loss.

    When an agent approves loans beyond its original calibrated range,
    the model is miscalibrated and produces more defaults. This is
    realistic: ML models perform poorly on out-of-distribution data.
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
            agent_profiles: {agent_id: risk_tolerance} where risk_tolerance
                            is the max risk_score the agent will approve.
            drift_agent_id: Which agent drifts over time. None = no drift.
            drift_rate: How much tolerance increases per cycle.
            drift_start_cycle: Cycle at which drift begins.
        """
        self.agent_profiles = dict(agent_profiles)
        self.original_profiles = dict(agent_profiles)  # Frozen calibration baseline
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

    def get_tolerance(self, agent_id: str) -> float:
        """Current risk tolerance for an agent."""
        return self.agent_profiles.get(agent_id, 0.5)

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Agent decides on a loan application.

        Decision logic:
        - If loan risk <= agent tolerance: APPROVE
        - If loan risk > agent tolerance: DENY

        Miscalibration logic:
        - If agent approves a loan beyond its original calibrated range,
          the model is operating on OOD data. A deterministic hash
          determines if the miscalibration causes an unexpected default.
        - The further outside the calibrated range, the higher the
          miscalibration probability.
        """
        start = time.monotonic()

        tolerance = self.get_tolerance(agent.id)
        original = self.original_profiles.get(agent.id, tolerance)
        loan_risk = task.risk
        defaulted = task.metadata.get("defaulted", False)
        amount = task.metadata.get("amount", 0)
        grade = task.metadata.get("grade", "?")

        approved = loan_risk <= tolerance

        miscalibrated = False
        if approved:
            # Check for model miscalibration on out-of-distribution approvals.
            # When an agent approves loans beyond its calibrated range, its
            # risk model is wrong — actual default rates are much higher than
            # predicted. This is the real phenomenon: OOD data breaks models.
            overreach = loan_risk - original
            if overreach > 0.03 and not defaulted:
                # Severe miscalibration: rate scales with overreach distance
                # At 0.10 overreach: 30% failure. At 0.25+: 65% failure.
                miscal_rate = min(0.65, overreach * 3.0)
                hash_val = hash(f"{task.id}_{agent.id}") % 1000
                if hash_val < miscal_rate * 1000:
                    defaulted = True
                    miscalibrated = True

            success = not defaulted
            decision = "APPROVED"
            if not success:
                outcome = "DEFAULTED_OOD" if miscalibrated else "DEFAULTED"
            else:
                outcome = "PERFORMING"
        else:
            success = True
            decision = "DENIED"
            outcome = "AVOIDED_LOSS" if defaulted else "DECLINED"

        latency = time.monotonic() - start

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=latency,
            metadata={
                "decision": decision,
                "outcome": outcome,
                "loan_amount": amount,
                "loan_grade": grade,
                "loan_risk": round(loan_risk, 3),
                "agent_tolerance": round(tolerance, 3),
                "original_tolerance": round(original, 3),
                "defaulted": defaulted,
                "miscalibrated": miscalibrated,
            }
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in self.agent_profiles
