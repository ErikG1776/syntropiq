"""
LLM Executor - Execute tasks using Large Language Models

Supports OpenAI (GPT-4, etc.) and Anthropic (Claude) as execution backends.
"""

import time
from typing import Optional
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.core.exceptions import AgentExecutionError, InvalidConfiguration
from syntropiq.execution.base import BaseExecutor


class LLMExecutor(BaseExecutor):
    """
    Execute tasks using LLM APIs.
    
    Agent IDs should match LLM model names:
    - "gpt-4", "gpt-3.5-turbo" (OpenAI)
    - "claude-3-opus", "claude-3-sonnet" (Anthropic)
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize LLM executor.
        
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on failure
        """
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Lazy import to avoid requiring these libraries if not used
        self.openai_client = None
        self.anthropic_client = None
        
    def _init_openai(self):
        """Initialize OpenAI client (lazy)."""
        if self.openai_client is None:
            if not self.openai_api_key:
                raise InvalidConfiguration("OpenAI API key required for OpenAI models")
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                raise InvalidConfiguration("openai package not installed. Run: pip install openai")
    
    def _init_anthropic(self):
        """Initialize Anthropic client (lazy)."""
        if self.anthropic_client is None:
            if not self.anthropic_api_key:
                raise InvalidConfiguration("Anthropic API key required for Claude models")
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            except ImportError:
                raise InvalidConfiguration("anthropic package not installed. Run: pip install anthropic")
    
    def execute(self, task: Task, agent: Agent) -> ExecutionResult:
        """
        Execute task using LLM.
        
        Task metadata should contain:
        - "prompt": The prompt to send to the LLM
        - "system_prompt": Optional system prompt
        
        Args:
            task: Task to execute
            agent: Agent (LLM model) to use
            
        Returns:
            ExecutionResult with success, latency, and response
        """
        start_time = time.time()
        
        # Extract prompt from task metadata
        prompt = task.metadata.get("prompt")
        if not prompt:
            raise AgentExecutionError(f"Task {task.id} missing 'prompt' in metadata")
        
        system_prompt = task.metadata.get("system_prompt", "You are a helpful AI assistant.")
        
        try:
            # Route to appropriate LLM provider
            if agent.id.startswith("gpt"):
                response = self._execute_openai(agent.id, prompt, system_prompt)
            elif agent.id.startswith("claude"):
                response = self._execute_anthropic(agent.id, prompt, system_prompt)
            else:
                raise AgentExecutionError(f"Unknown LLM model: {agent.id}")
            
            latency = time.time() - start_time
            
            return ExecutionResult(
                task_id=task.id,
                agent_id=agent.id,
                success=True,
                latency=latency,
                metadata={"response": response}
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
    
    def _execute_openai(self, model: str, prompt: str, system_prompt: str) -> str:
        """Execute using OpenAI API."""
        self._init_openai()
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            timeout=self.timeout
        )
        
        return response.choices[0].message.content
    
    def _execute_anthropic(self, model: str, prompt: str, system_prompt: str) -> str:
        """Execute using Anthropic API."""
        self._init_anthropic()
        
        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=self.timeout
        )
        
        return response.content[0].text
    
    def validate_agent(self, agent: Agent) -> bool:
        """Validate that agent is a supported LLM model."""
        supported_prefixes = ["gpt", "claude"]
        return any(agent.id.startswith(prefix) for prefix in supported_prefixes)