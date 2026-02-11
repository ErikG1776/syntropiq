"""
Deterministic Executor - Reproducible execution backend for tests.

Removes randomness by using a fixed scoring rule:
success = (agent.trust_score - task.risk) >= decision_threshold
"""

from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.execution.base import BaseExecutor


class DeterministicExecutor(BaseExecutor):
    """
    Deterministic task executor for testing and regression checks.

    Args:
        decision_threshold: Minimum (trust_score - risk) value required for success.
        fixed_latency: Latency to report for every execution result.
    """

    def __init__(self, decision_threshold: float = 0.0, fixed_latency: float = 0.001):
        self.decision_threshold = decision_threshold
        self.fixed_latency = fixed_latency

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        score = agent.trust_score - task.risk
        success = score >= self.decision_threshold

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=self.fixed_latency,
            metadata={
                "deterministic": True,
                "score": round(score, 6),
                "decision_threshold": self.decision_threshold,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return bool(agent.id)
