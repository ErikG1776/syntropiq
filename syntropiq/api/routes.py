"""
API Routes - REST Endpoints for Syntropiq

Provides endpoints for:
- Task submission and governance execution
- Agent registration and management
- System monitoring and statistics
- Governance history and reflections
- Governance telemetry (events, cycles, streaming)
"""

import asyncio
import json
import queue
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from syntropiq.core.models import Task
from syntropiq.api.schemas import (
    AgentRegistrationRequest,
    AgentResponse,
    GovernanceCycleResponse,
    GovernanceCycleResponseV1,
    GovernanceEventV1,
    SystemStatisticsResponse,
    TaskSubmissionRequest,
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

    tasks = [
        Task(
            id=task.id,
            impact=task.impact,
            urgency=task.urgency,
            risk=task.risk,
            metadata=task.metadata or {},
        )
        for task in request.tasks
    ]

    agents = server.agent_registry.get_agents_dict()
    if not agents:
        raise HTTPException(status_code=400, detail="No agents registered")

    try:
        result = server.governance_loop.execute_cycle(
            tasks=tasks,
            agents=agents,
            executor=server.executor,
            run_id=request.run_id or "API_CYCLE",
        )

        server.agent_registry.sync_trust_scores()

        server.mutation_engine.trust_threshold = result["mutation"]["trust_threshold"]
        server.mutation_engine.suppression_threshold = result["mutation"][
            "suppression_threshold"
        ]
        server.mutation_engine.drift_delta = result["mutation"]["drift_delta"]

        return GovernanceCycleResponse(
            run_id=result["run_id"],
            tasks_executed=result["statistics"]["tasks_executed"],
            successes=result["statistics"]["successes"],
            failures=result["statistics"]["failures"],
            avg_latency=result["statistics"]["avg_latency"],
            trust_updates=result["trust_updates"],
            reflection=result["reflection"],
            mutation=result["mutation"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/register", response_model=AgentResponse)
def register_agent(request: AgentRegistrationRequest):
    """Register a new agent."""

    try:
        agent = server.agent_registry.register_agent(
            agent_id=request.agent_id,
            capabilities=request.capabilities,
            initial_trust_score=request.initial_trust_score,
            status=request.status,
        )

        return AgentResponse(
            agent_id=agent.id,
            trust_score=agent.trust_score,
            capabilities=agent.capabilities,
            status=agent.status,
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
            status=agent.status,
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
        "governance_status": status,
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
        mutation_performance=mutation_stats,

        # --- NEW ---
        trust_threshold=server.mutation_engine.trust_threshold,
        suppression_threshold=server.mutation_engine.suppression_threshold,
        drift_delta=server.mutation_engine.drift_delta,
    )


@router.get("/events", response_model=List[GovernanceEventV1])
def get_events(since: Optional[str] = Query(default=None)):
    if server.telemetry_hub is None:
        return []
    try:
        return server.telemetry_hub.get_events_since(since)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid since timestamp: {e}")


@router.get("/cycles", response_model=List[GovernanceCycleResponseV1])
def get_cycles(limit: int = Query(default=20, ge=1, le=500)):
    if server.telemetry_hub is None:
        return []
    return server.telemetry_hub.get_cycles(limit=limit)


@router.get("/events/stream")
async def stream_events(request: Request):
    if server.telemetry_hub is None:
        async def empty_stream():
            yield ": telemetry_unavailable\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    token, subscriber = server.telemetry_hub.subscribe(max_queue_size=1000)

    async def event_stream():
        yield "retry: 1000\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(subscriber.get, True, 1.0)
                    payload = json.dumps(event.model_dump())
                    yield f"event: governance_event\ndata: {payload}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            server.telemetry_hub.unsubscribe(token)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.get("/reflections")
def get_reflections(limit: int = 10):
    reflections = server.state_manager.get_recent_reflections(limit=limit)
    return {"reflections": reflections}


@router.get("/mutation/history")
def get_mutation_history(limit: int = 10):
    history = server.mutation_engine.get_mutation_history(limit=limit)
    return {"mutation_history": history}
