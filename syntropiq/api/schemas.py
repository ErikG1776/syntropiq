"""
API Schemas - Request/Response Models

Pydantic models for API validation and documentation.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


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
    initial_trust_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Starting trust score"
    )
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

    # --- Governance Thresholds ---
    trust_threshold: float
    suppression_threshold: float
    drift_delta: float


class GovernanceEventType(str, Enum):
    trust_update = "trust_update"
    suppression = "suppression"
    mutation = "mutation"
    reflection = "reflection"
    probation = "probation"
    status_change = "status_change"
    threshold_breach = "threshold_breach"
    system_alert = "system_alert"


class GovernanceEventV1(BaseModel):
    run_id: str
    cycle_id: str
    timestamp: str
    type: GovernanceEventType
    agent_id: Optional[str] = None
    trust_before: float
    trust_after: float
    authority_before: float
    authority_after: float
    metadata: Dict = Field(default_factory=dict)


class GovernanceCycleResponseV1(BaseModel):
    run_id: str
    cycle_id: str
    timestamp: str
    total_agents: int
    successes: int
    failures: int
    trust_delta_total: float
    authority_redistribution: Dict[str, float] = Field(default_factory=dict)
    events: List[GovernanceEventV1] = Field(default_factory=list)
