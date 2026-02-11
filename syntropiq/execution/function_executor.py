"""
Function Executor - Execute tasks using Python functions/callables

Allows any Python function or callable to be used as an agent.
Perfect for ML models, rule-based systems, or custom business logic.
"""

import time
from typing import Callable, Dict
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.core.exceptions import AgentExecutionError
from syntropiq.execution.base import BaseExecutor


class FunctionExecutor(BaseExecutor):
    """
    Execute tasks using Python functions.

    Agents are registered as callable functions that take a task and return a result.

    The return value of the function determines success:

        - If function returns:
            • bool → used directly as success
            • dict with {"success": bool} → used as success
            • any truthy value → success=True
            • falsy value → success=False
    """

    def __init__(self):
        """Initialize function executor with empty registry."""
        self.functions: Dict[str, Callable] = {}

    def register_function(self, agent_id: str, func: Callable):
        """
        Register a function as an executable agent.

        Args:
            agent_id: Unique identifier for this agent
            func: Callable that takes (task: Task) and returns a result
        """
        if not callable(func):
            raise AgentExecutionError(
                f"Registered agent {agent_id} is not callable"
            )

        self.functions[agent_id] = func
        print(f"✅ Registered function agent: {agent_id}")

    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Execute task using registered function.

        Returns:
            ExecutionResult with success determined by function output.
        """
        start_time = time.time()

        if agent.id not in self.functions:
            raise AgentExecutionError(
                f"Agent {agent.id} not registered. Use register_function() first."
            )

        func = self.functions[agent.id]

        try:
            result = func(task)
            latency = time.time() - start_time

            # 🔥 Determine success from function output
            if isinstance(result, bool):
                success = result
            elif isinstance(result, dict) and "success" in result:
                success = bool(result["success"])
            else:
                success = bool(result)

            return ExecutionResult(
                task_id=task.id,
                agent_id=agent.id,
                success=success,
                latency=latency,
                metadata={"result": result}
            )

        except Exception as e:
            latency = time.time() - start_time
            return ExecutionResult(
                task_id=task.id,
                agent_id=agent.id,
                success=False,
                latency=latency,
                metadata={"error": str(e)}
            )

    def validate_agent(self, agent: Agent) -> bool:
        """Validate that agent is registered as a function."""
        return agent.id in self.functions

    def list_registered_agents(self) -> list:
        """Get list of all registered agent IDs."""
        return list(self.functions.keys())