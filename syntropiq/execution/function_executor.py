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
    
    Example:
        def fraud_detector(task):
            # Your ML model logic here
            prediction = model.predict(task.metadata['transaction'])
            return {"fraud_detected": prediction > 0.5}
        
        executor = FunctionExecutor()
        executor.register_function("fraud_model", fraud_detector)
    """
    
    def __init__(self):
        """Initialize function executor with empty registry."""
        self.functions: Dict[str, Callable] = {}
    
    def register_function(self, agent_id: str, func: Callable):
        """
        Register a function as an executable agent.
        
        Args:
            agent_id: Unique identifier for this agent
            func: Callable that takes (task: Task) and returns a dict
        """
        if not callable(func):
            raise AgentExecutionError(f"Registered agent {agent_id} is not callable")
        
        self.functions[agent_id] = func
        print(f"✅ Registered function agent: {agent_id}")
    
    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Execute task using registered function.
        
        Args:
            task: Task to execute
            agent: Agent to use (must be registered)
            
        Returns:
            ExecutionResult with success, latency, and function output
        """
        start_time = time.time()
        
        # Check if agent is registered
        if agent.id not in self.functions:
            raise AgentExecutionError(
                f"Agent {agent.id} not registered. Use register_function() first."
            )
        
        func = self.functions[agent.id]
        
        try:
            # Execute function
            result = func(task)
            latency = time.time() - start_time
            
            return ExecutionResult(
                task_id=task.id,
                agent_id=agent.id,
                success=True,
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