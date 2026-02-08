from typing import List, Optional
from pydantic import BaseModel

class Task(BaseModel):
    id: str
    impact: float
    urgency: float
    risk: float
    metadata: Optional[dict] = {}

class Agent(BaseModel):
    id: str
    trust_score: float
    capabilities: List[str]
    status: str

class Assignment(BaseModel):
    task_id: str
    agent_id: str

class ExecutionResult(BaseModel):
    task_id: str
    agent_id: str
    success: bool
    latency: float
    metadata: Optional[dict] = {}

# ✅ Loader for baseline agent pool (used if trust memory is empty)
def default_agents() -> List[Agent]:
    return [
        Agent(id="RuleModel", trust_score=0.64, capabilities=["fraud"], status="active"),
        Agent(id="MLModel", trust_score=0.65, capabilities=["fraud"], status="active"),
        Agent(id="VendorAPI", trust_score=0.68, capabilities=["fraud"], status="active"),
    ]

