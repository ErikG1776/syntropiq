"""
Fraud Detection Executor

Simulates AI agents making fraud pass/flag decisions on payment transactions.
Each agent has a fraud threshold that determines its flagging boundary.

One agent ("drift_agent") gradually increases its threshold over cycles,
simulating real-world model drift where an agent starts passing transactions
it should flag. Syntropiq's governance catches this.

Outcome model (maps identically to lending):
- Flagged any transaction   = SUCCESS (conservative action is always safe)
- Passed a legit transaction = SUCCESS (correct clearance)
- Passed a fraud transaction = FAILURE (missed fraud — the dangerous outcome)

Miscalibration model:
When an agent passes a transaction significantly beyond its ORIGINAL calibrated
range, its model is operating on out-of-distribution data.  The actual
fraud rate is higher than predicted.  This concentrates failures on
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


class FraudDetectionExecutor(BaseExecutor):
    """
    Simulates fraud detection agents with configurable sensitivity profiles.

    Each agent has a fraud_threshold: the maximum transaction risk_score
    they'll PASS (allow through).  Above that threshold they FLAG (block).

    If an agent passes a transaction that turns out to be fraud, that's
    a failure.  Flagging is always safe — a flag never causes a loss.

    When an agent passes transactions beyond its original calibrated range,
    the model is miscalibrated and produces more missed fraud.
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
            agent_profiles: {agent_id: fraud_threshold} where fraud_threshold
                            is the max risk_score the agent will PASS.
            drift_agent_id: Which agent drifts over time. None = no drift.
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
        """Current fraud threshold for an agent."""
        return self.agent_profiles.get(agent_id, 0.5)

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Agent decides on a transaction.

        Decision logic:
        - If transaction risk <= agent threshold: PASS (allow through)
        - If transaction risk > agent threshold: FLAG (block)

        Miscalibration logic:
        - If agent passes a transaction beyond its original calibrated range,
          the model is operating on OOD data.  A deterministic hash decides
          whether the miscalibration causes an unexpected fraud.
        - The further outside the calibrated range, the higher the
          miscalibration probability.
        """
        start = time.monotonic()

        threshold = self.get_threshold(agent.id)
        original = self.original_profiles.get(agent.id, threshold)
        tx_risk = task.risk
        is_fraud = task.metadata.get("is_fraud", False)
        amount = task.metadata.get("amount", 0)
        risk_tier = task.metadata.get("risk_tier", "?")

        passed = tx_risk <= threshold

        miscalibrated = False
        if passed:
            # Check for model miscalibration on out-of-distribution passes.
            # When an agent passes transactions beyond its calibrated range,
            # its risk model is wrong — actual fraud rates are much higher
            # than predicted.
            overreach = tx_risk - original
            if overreach > 0.03 and not is_fraud:
                # Severe miscalibration: rate scales with overreach distance
                # At 0.10 overreach: 30% failure. At 0.25+: 65% failure.
                miscal_rate = min(0.65, overreach * 3.0)
                hash_val = _stable_hash(f"{task.id}_{agent.id}") % 1000
                if hash_val < miscal_rate * 1000:
                    is_fraud = True
                    miscalibrated = True

            success = not is_fraud
            decision = "PASSED"
            if not success:
                outcome = "MISSED_FRAUD_OOD" if miscalibrated else "MISSED_FRAUD"
            else:
                outcome = "CLEARED"
        else:
            success = True
            decision = "FLAGGED"
            outcome = "CAUGHT_FRAUD" if is_fraud else "FALSE_POSITIVE"

        latency = time.monotonic() - start

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=latency,
            metadata={
                "decision": decision,
                "outcome": outcome,
                "tx_amount": amount,
                "risk_tier": risk_tier,
                "tx_risk": round(tx_risk, 3),
                "agent_threshold": round(threshold, 3),
                "original_threshold": round(original, 3),
                "is_fraud": is_fraud,
                "miscalibrated": miscalibrated,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in self.agent_profiles
