"""
Finance Allocation Executor

Simulates capital-allocation agents making weekly investment decisions.
Each agent has a fixed allocation across tickers. The executor evaluates
whether the agent's allocation outperformed the benchmark that week.

Domain mapping (identical structure to lending/fraud/readmission executors):
    Loan approval        -> Capital allocation
    Default event        -> Underperformance vs benchmark
    Default severity     -> Magnitude of underperformance delta
    Recovery             -> Outperformance vs benchmark
    Dollar loss          -> Portfolio underperformance in dollars

Outcome model:
- Agent outperforms benchmark  = SUCCESS (alpha generated)
- Agent underperforms benchmark = FAILURE (benchmark miss)

This is the ONLY domain-specific code. All trust updates, suppression,
mutation, and authority weighting come from the real Syntropiq kernel.
"""

import hashlib
import time
from typing import Dict

from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.execution.base import BaseExecutor


def _stable_hash(s: str) -> float:
    """Deterministic noise in [-0.001, 0.001]."""
    h = int(hashlib.sha256(s.encode()).hexdigest(), 16)
    return ((h % 2000) - 1000) / 1000000.0


# Agent allocation definitions
AGENT_ALLOCATIONS = {
    "growth": {"QQQ": 0.70, "SPY": 0.20, "TLT": 0.10},
    "risk":   {"QQQ": 0.15, "SPY": 0.25, "TLT": 0.60},
    "macro":  {"QQQ": 0.35, "SPY": 0.45, "TLT": 0.20},
}


class FinanceAllocationExecutor(BaseExecutor):
    """
    Simulates capital-allocation agents evaluated against a benchmark.

    Each agent has a fixed allocation across tickers. Each week the executor
    computes the agent's weighted return from market data, compares it to the
    benchmark return, and produces a success/failure signal.

    This executor does NO trust math, NO suppression logic, NO mutation.
    It only answers: "Did this agent outperform or underperform this week?"

    The Syntropiq kernel handles everything else.
    """

    def __init__(self, agent_allocations: Dict[str, Dict[str, float]] = None):
        self.agent_allocations = agent_allocations or dict(AGENT_ALLOCATIONS)

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Evaluate an agent's allocation performance for one week.

        The task metadata contains:
            - ticker_returns: {ticker: weekly_return}
            - benchmark_return: float
            - week_num: int
            - regime: str

        Decision logic:
            - Compute agent's weighted return from its allocation
            - Compare to benchmark return
            - Outperform (delta >= -0.0005) = SUCCESS
            - Underperform (delta < -0.0005) = FAILURE
        """
        start = time.monotonic()

        ticker_returns = task.metadata.get("ticker_returns", {})
        benchmark_return = task.metadata.get("benchmark_return", 0.0)
        week_num = task.metadata.get("week_num", 0)
        regime = task.metadata.get("regime", "unknown")

        alloc = self.agent_allocations.get(agent.id, {})

        # Compute agent's weighted return
        agent_return = sum(
            alloc.get(ticker, 0.0) * ticker_returns.get(ticker, 0.0)
            for ticker in alloc
        )
        noise = _stable_hash(f"agent_{agent.id}_week_{week_num}")
        agent_return += noise

        benchmark_delta = agent_return - benchmark_return

        # Outperform = success, underperform = failure
        # Small noise band: delta >= -0.0005 counts as meeting benchmark
        success = benchmark_delta >= -0.0005

        if success:
            decision = "OUTPERFORMED"
            outcome = "ALPHA_GENERATED"
        else:
            decision = "UNDERPERFORMED"
            magnitude = abs(benchmark_delta)
            if magnitude < 0.003:
                outcome = "BENCHMARK_MISS_MILD"
            elif magnitude < 0.006:
                outcome = "BENCHMARK_MISS_MODERATE"
            else:
                outcome = "BENCHMARK_MISS_SEVERE"

        latency = time.monotonic() - start

        return ExecutionResult(
            task_id=task.id,
            agent_id=agent.id,
            success=success,
            latency=latency,
            metadata={
                "decision": decision,
                "outcome": outcome,
                "weekly_return": round(agent_return, 6),
                "benchmark_return": round(benchmark_return, 6),
                "benchmark_delta": round(benchmark_delta, 6),
                "regime": regime,
                "week_num": week_num,
                "allocation": alloc,
            },
        )

    def validate_agent(self, agent: Agent) -> bool:
        return agent.id in self.agent_allocations
