"""
API Routes - REST Endpoints for Syntropiq

Provides endpoints for:
- Task submission and governance execution
- Agent registration and management
- System monitoring and statistics
- Governance history and reflections
"""

from fastapi import APIRouter, HTTPException
from typing import List
from syntropiq.core.models import Task, Agent
from syntropiq.api.schemas import (
    TaskSubmissionRequest,
    AgentRegistrationRequest,
    AgentResponse,
    GovernanceCycleResponse,
    SystemStatisticsResponse
)
import syntropiq.api.server as server


router = APIRouter(prefix="/api/v1", tags=["syntropiq"])


@router.post("/tasks/submit", response_model=GovernanceCycleResponse)
def submit_tasks(request: TaskSubmissionRequest):
    """
    Submit tasks for governance and execution.

    This endpoint:
    1. Receives tasks
    2. Runs full governance cycle
    3. Returns results with trust updates
    """

    # Convert request into Task objects
    tasks = [
        Task(
            id=task.id,
            impact=task.impact,
            urgency=task.urgency,
            risk=task.risk,
            metadata=task.metadata or {}
        )
        for task in request.tasks
    ]

    # IMPORTANT CHANGE:
    # We no longer filter by status="active".
    # Governance engine must receive all agents
    # so it can evaluate suppression, probation, drift internally.
    agents = server.agent_registry.get_agents_dict()

    if not agents:
        raise HTTPException(status_code=400, detail="No agents registered")

    try:
        result = server.governance_loop.execute_cycle(
            tasks=tasks,
            agents=agents,
            executor=server.executor,
            run_id=request.run_id or "API_CYCLE"
        )

        # Run mutation engine
        mutation_result = server.mutation_engine.evaluate_and_mutate(
            execution_results=result["results"],
            cycle_id=result["run_id"]
        )

        # Live-sync thresholds into trust engine
        server.governance_loop.trust_engine.trust_threshold = mutation_result["trust_threshold"]
        server.governance_loop.trust_engine.suppression_threshold = mutation_result["suppression_threshold"]
        server.governance_loop.trust_engine.drift_delta = mutation_result["drift_delta"]

        # Sync trust scores into registry
        server.agent_registry.sync_trust_scores()

        return GovernanceCycleResponse(
            run_id=result["run_id"],
            tasks_executed=result["statistics"]["tasks_executed"],
            successes=result["statistics"]["successes"],
            failures=result["statistics"]["failures"],
            avg_latency=result["statistics"]["avg_latency"],
            trust_updates=result["trust_updates"],
            reflection=result["reflection"],
            mutation=mutation_result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/register", response_model=AgentResponse)
def register_agent(request: AgentRegistrationRequest):
    """
    Register a new agent.
    """

    try:
        agent = server.agent_registry.register_agent(
            agent_id=request.agent_id,
            capabilities=request.capabilities,
            initial_trust_score=request.initial_trust_score,
            status=request.status
        )

        return AgentResponse(
            agent_id=agent.id,
            trust_score=agent.trust_score,
            capabilities=agent.capabilities,
            status=agent.status
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(status: str = None):
    agents = server.agent_registry.list_agents(status=status)

    return [
        AgentResponse(
            agent_id=agent.id,
            trust_score=agent.trust_score,
            capabilities=agent.capabilities,
            status=agent.status
        )
        for agent in agents
    ]


@router.get("/agents/{agent_id}")
def get_agent_status(agent_id: str):
    agent = server.agent_registry.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    status = server.governance_loop.get_agent_status(agent_id)

    return {
        "agent_id": agent.id,
        "trust_score": agent.trust_score,
        "capabilities": agent.capabilities,
        "status": agent.status,
        "governance_status": status
    }


@router.put("/agents/{agent_id}/status")
def update_agent_status(agent_id: str, status: str):
    try:
        server.agent_registry.update_agent_status(agent_id, status)
        return {"agent_id": agent_id, "new_status": status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/statistics", response_model=SystemStatisticsResponse)
def get_statistics():
    db_stats = server.state_manager.get_statistics()
    agent_stats = server.agent_registry.get_agent_statistics()
    mutation_stats = server.mutation_engine.get_performance_trend()

    return SystemStatisticsResponse(
        total_executions=db_stats["total_executions"],
        success_rate=db_stats["success_rate"],
        suppressed_agents=db_stats["suppressed_agents"],
        valid_reflections=db_stats["valid_reflections"],
        total_agents=agent_stats["total_agents"],
        active_agents=agent_stats["active_agents"],
        avg_trust_score=agent_stats["avg_trust_score"],
        mutation_performance=mutation_stats
    )


@router.get("/reflections")
def get_reflections(limit: int = 10):
    reflections = server.state_manager.get_recent_reflections(limit=limit)
    return {"reflections": reflections}


@router.get("/mutation/history")
def get_mutation_history(limit: int = 10):
    history = server.mutation_engine.get_mutation_history(limit=limit)
    return {"mutation_history": history}
