"""
API Schemas - Request/Response Models

Pydantic models for API validation and documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class TaskSchema(BaseModel):
    """Task submission schema."""
    id: str
    impact: float = Field(..., ge=0.0, le=1.0, description="Impact score (0.0-1.0)")
    urgency: float = Field(..., ge=0.0, le=1.0, description="Urgency score (0.0-1.0)")
    risk: float = Field(..., ge=0.0, le=1.0, description="Risk score (0.0-1.0)")
    metadata: Optional[Dict] = Field(default={}, description="Task metadata")


class TaskSubmissionRequest(BaseModel):
    """Request to submit tasks for governance execution."""
    tasks: List[TaskSchema]
    run_id: Optional[str] = Field(None, description="Optional cycle identifier")


class GovernanceCycleResponse(BaseModel):
    """Response from governance cycle execution."""
    run_id: str
    tasks_executed: int
    successes: int
    failures: int
    avg_latency: float
    trust_updates: Dict[str, float]
    reflection: Dict
    mutation: Dict[str, float]


class AgentRegistrationRequest(BaseModel):
    """Request to register a new agent."""
    agent_id: str = Field(..., description="Unique agent identifier")
    capabilities: List[str] = Field(..., description="List of agent capabilities")
    initial_trust_score: float = Field(0.5, ge=0.0, le=1.0, description="Starting trust score")
    status: str = Field("active", description="Agent status (active/inactive/suspended)")


class AgentResponse(BaseModel):
    """Agent information response."""
    agent_id: str
    trust_score: float
    capabilities: List[str]
    status: str


class SystemStatisticsResponse(BaseModel):
    """System-wide statistics response."""
    total_executions: int
    success_rate: float
    suppressed_agents: int
    valid_reflections: int
    total_agents: int
    active_agents: int
    avg_trust_score: float
    mutation_performance: Dict