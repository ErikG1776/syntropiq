"""
Base Executor Interface

Abstract interface that all executors must implement.
Allows Syntropiq to work with different execution backends (LLMs, functions, APIs, etc.)
"""

from abc import ABC, abstractmethod
from syntropiq.core.models import Task, Agent, ExecutionResult


class BaseExecutor(ABC):
    """
    Abstract base class for all executors.
    
    Executors handle the actual execution of tasks by agents.
    Different implementations can execute via:
    - LLMs (OpenAI, Anthropic, etc.)
    - Python functions
    - External APIs
    - Simulators (for testing)
    """
    
    @abstractmethod
    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Execute a task with the given agent.
        
        Args:
            task: The task to execute
            agent: The agent executing the task
            
        Returns:
            ExecutionResult with success status, latency, and metadata
        """
        pass
    
    @abstractmethod
    def validate_agent(self, agent: Agent) -> bool:
        """
        Validate that this executor can handle the given agent.
        
        Args:
            agent: The agent to validate
            
        Returns:
            True if executor can handle this agent, False otherwise
        """
        pass