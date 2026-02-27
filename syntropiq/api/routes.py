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
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from syntropiq.core.models import Task
from syntropiq.api.schemas import (
    AgentRegistrationRequest,
    AgentResponse,
    GovernanceCycleResponse,
    GovernanceCycleResponseV1,
    GovernanceEventV1,
    SystemStatisticsResponse,
    TaskSchema,
    TaskSubmissionRequest,
)
import syntropiq.api.server as server


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_event(event: dict):
    if server.telemetry_hub is None:
        return
    server.telemetry_hub.publish_events([event])


CIRCUIT_STATE = {
    "active": False,
    "cooldown_cycles": 0
}


def _emit_circuit_breaker(run_id: str, reason: str):
    timestamp = _utc_ts()
    tau = (
        float(getattr(server.mutation_engine, "trust_threshold", 0.0))
        if server.mutation_engine is not None
        else 0.0
    )
    cycle_id = f"{run_id}:circuit:{uuid.uuid4().hex[:8]}"
    event = {
        "run_id": run_id,
        "cycle_id": cycle_id,
        "timestamp": timestamp,
        "type": "circuit_breaker",
        "agent_id": None,
        "trust_before": 0.0,
        "trust_after": 0.0,
        "authority_before": 0.0,
        "authority_after": 0.0,
        "metadata": {
            "reason": reason,
            "tau": tau,
        },
    }
    _emit_event(event)
    if server.telemetry_hub is not None:
        server.telemetry_hub.record_cycle(
            {
                "run_id": run_id,
                "cycle_id": cycle_id,
                "timestamp": timestamp,
                "total_agents": 0,
                "successes": 0,
                "failures": 1,
                "trust_delta_total": 0.0,
                "authority_redistribution": {},
                "events": [event],
            }
        )


def select_highest_trust(eligible_agents):
    sorted_agents = sorted(
        eligible_agents.items(),
        key=lambda x: x[1]["trust_score"],
        reverse=True
    )
    return [sorted_agents[0][0]] if sorted_agents else []


def select_top_n_trust(eligible_agents, n=2):
    sorted_agents = sorted(
        eligible_agents.items(),
        key=lambda x: x[1]["trust_score"],
        reverse=True
    )
    return [agent_id for agent_id, _ in sorted_agents[:n]]


def select_round_robin(eligible_agents):
    return list(eligible_agents.keys())[:1]


STRATEGY_REGISTRY = {
    "highest_trust_v1": select_highest_trust,
    "top_n_trust_v1": select_top_n_trust,
    "round_robin_v1": select_round_robin,
}


class GovernanceExecuteRequest(BaseModel):
    task: TaskSchema
    run_id: Optional[str] = None
    strategy: Optional[str] = None


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


@router.post("/governance/execute")
def governance_execute(request: GovernanceExecuteRequest):
    task_obj = Task(
        id=request.task.id,
        impact=request.task.impact,
        urgency=request.task.urgency,
        risk=request.task.risk,
        metadata=request.task.metadata or {},
    )

    run_id = request.run_id or "EXEC_GATEWAY"

    # Load all agents
    agents_dict = server.agent_registry.get_agents_dict()

    # Filter suppressed agents
    eligible_agents = [
        agent for agent in agents_dict.values()
        if agent.status != "suppressed"
    ]

    if CIRCUIT_STATE["active"] and len(eligible_agents) > 0:
        CIRCUIT_STATE["active"] = False
        CIRCUIT_STATE["cooldown_cycles"] = 0
        _emit_event(
            {
                "run_id": run_id,
                "cycle_id": f"{run_id}:circuit:{uuid.uuid4().hex[:8]}",
                "timestamp": _utc_ts(),
                "type": "circuit_breaker",
                "agent_id": None,
                "trust_before": 0.0,
                "trust_after": 0.0,
                "authority_before": 0.0,
                "authority_after": 0.0,
                "metadata": {
                    "reason": "circuit_reset",
                    "eligible_agents": [a.id for a in eligible_agents],
                    "tau": float(getattr(server.mutation_engine, "trust_threshold", 0.0)),
                },
            }
        )

    if CIRCUIT_STATE["active"]:
        CIRCUIT_STATE["cooldown_cycles"] -= 1
        reason = "cooldown_active"
        if CIRCUIT_STATE["cooldown_cycles"] <= 0:
            CIRCUIT_STATE["active"] = False
            CIRCUIT_STATE["cooldown_cycles"] = 0
            reason = "cooldown_release_block"
        _emit_circuit_breaker(run_id=run_id, reason=reason)
        return JSONResponse(
            status_code=503,
            content={"error": "no_eligible_agents"}
        )

    if not eligible_agents:
        CIRCUIT_STATE["active"] = True
        CIRCUIT_STATE["cooldown_cycles"] = 1
        _emit_circuit_breaker(run_id=run_id, reason="no_eligible_agents")
        return JSONResponse(
            status_code=503,
            content={"error": "no_eligible_agents"}
        )

    total_trust = sum(float(getattr(agent, "trust_score", 0.0)) for agent in eligible_agents)
    authority_distribution = {}
    for agent_id, agent in agents_dict.items():
        if getattr(agent, "status", None) == "suppressed":
            authority_distribution[agent_id] = 0.0
        elif total_trust > 0:
            authority_distribution[agent_id] = float(getattr(agent, "trust_score", 0.0)) / total_trust
        else:
            authority_distribution[agent_id] = 1.0 / max(1, len(eligible_agents))

    strategy_name = request.strategy or "highest_trust_v1"

    if strategy_name not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=400, detail="unknown_strategy")

    selector = STRATEGY_REGISTRY[strategy_name]

    eligible_agent_map = {
        agent.id: {
            "trust_score": agent.trust_score,
            "agent": agent,
        }
        for agent in eligible_agents
    }

    if strategy_name == "top_n_trust_v1":
        selected_ids = selector(eligible_agent_map, n=2)
    else:
        selected_ids = selector(eligible_agent_map)

    selected_agent_map = {
        agent_id: eligible_agent_map[agent_id]["agent"]
        for agent_id in selected_ids
        if agent_id in eligible_agent_map
    }

    mediation_metadata = {
        "eligible_agents": list(eligible_agent_map.keys()),
        "selected_agents": selected_ids,
        "selection_strategy": strategy_name,
        "strategy_name": strategy_name,
        "n": len(selected_ids),
        "authority_before": authority_distribution,
        "authority_after": authority_distribution,
        "authority_distribution": authority_distribution,
    }
    print(f"[governance/execute] mediation={mediation_metadata}")
    timestamp = _utc_ts()
    selected_agent_id = mediation_metadata.get("selected_agents", [None])[0]

    mediation_event = {
        "run_id": run_id,
        "cycle_id": f"{run_id}:mediation:{uuid.uuid4().hex[:8]}",
        "timestamp": timestamp,
        "type": "mediation_decision",
        "agent_id": selected_agent_id,
        "trust_before": 0.0,
        "trust_after": 0.0,
        "authority_before": 0.0,
        "authority_after": 0.0,
        "metadata": {
            **(mediation_metadata or {}),
            "task_id": getattr(request.task, "id", None),
        },
    }
    _emit_event(mediation_event)

    trust_before = {
        aid: float(getattr(agent, "trust_score", 0.0))
        for aid, agent in selected_agent_map.items()
    }

    try:
        result = server.governance_loop.execute_cycle(
            tasks=[task_obj],
            agents=selected_agent_map,
            executor=server.executor,
            run_id=run_id,
        )

        server.agent_registry.sync_trust_scores()

        server.mutation_engine.trust_threshold = result["mutation"]["trust_threshold"]
        server.mutation_engine.suppression_threshold = result["mutation"][
            "suppression_threshold"
        ]
        server.mutation_engine.drift_delta = result["mutation"]["drift_delta"]

        if server.telemetry_hub is not None:
            run_id = result["run_id"]
            cycle_id = str(result.get("cycle_id", result["run_id"]))
            timestamp = result.get("timestamp") or _utc_ts()
            authority_baseline = 1.0 / max(1, len(selected_agent_map))

            events = []
            for agent_id, trust_after in result["trust_updates"].items():
                before = float(trust_before.get(agent_id, trust_after))
                after = float(trust_after)
                events.append(
                    {
                        "run_id": run_id,
                        "cycle_id": cycle_id,
                        "timestamp": timestamp,
                        "type": "trust_update",
                        "agent_id": agent_id,
                        "trust_before": round(before, 6),
                        "trust_after": round(after, 6),
                        "authority_before": round(authority_baseline, 6),
                        "authority_after": round(authority_baseline, 6),
                        "metadata": {
                            "delta": round(after - before, 6),
                        },
                    }
                )

            events.append(
                {
                    "run_id": run_id,
                    "cycle_id": cycle_id,
                    "timestamp": timestamp,
                    "type": "mutation",
                    "agent_id": None,
                    "trust_before": 0.0,
                    "trust_after": 0.0,
                    "authority_before": 0.0,
                    "authority_after": 0.0,
                    "metadata": dict(result.get("mutation", {})),
                }
            )

            events.append(
                {
                    "run_id": run_id,
                    "cycle_id": cycle_id,
                    "timestamp": timestamp,
                    "type": "reflection",
                    "agent_id": None,
                    "trust_before": 0.0,
                    "trust_after": 0.0,
                    "authority_before": 0.0,
                    "authority_after": 0.0,
                    "metadata": dict(result.get("reflection", {})),
                }
            )

            server.telemetry_hub.publish_events(events)
            server.telemetry_hub.record_cycle(
                {
                    "run_id": run_id,
                    "cycle_id": cycle_id,
                    "timestamp": timestamp,
                    "total_agents": len(selected_agent_map),
                    "successes": result["statistics"]["successes"],
                    "failures": result["statistics"]["failures"],
                    "trust_delta_total": round(
                        sum(
                            float(
                                result["trust_updates"].get(
                                    aid, trust_before.get(aid, 0.0)
                                )
                            )
                            - float(trust_before.get(aid, 0.0))
                            for aid in selected_agent_map.keys()
                        ),
                        6,
                    ),
                    "authority_redistribution": {
                        aid: 0.0 for aid in selected_agent_map.keys()
                    },
                    "events": events,
                }
            )

        return {
            "run_id": result["run_id"],
            "tasks_executed": result["statistics"]["tasks_executed"],
            "successes": result["statistics"]["successes"],
            "failures": result["statistics"]["failures"],
            "avg_latency": result["statistics"]["avg_latency"],
            "trust_updates": result["trust_updates"],
            "mutation": result["mutation"],
            "reflection": result["reflection"],
            "mediation": mediation_metadata,
        }
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
    prev = server.agent_registry.get_agent(agent_id)
    prev_status = prev.status if prev else None
    prev_trust = prev.trust_score if prev else 0.0

    try:
        server.agent_registry.update_agent_status(agent_id, status)

        timestamp = _utc_ts()
        run_id = "MANUAL_OVERRIDE"
        cycle_id = f"{run_id}:{uuid.uuid4().hex[:8]}"

        event_type = None
        if status == "suppressed":
            event_type = "suppression"
        elif status == "active" and prev_status == "suppressed":
            event_type = "restoration"

        if event_type:
            evt = {
                "run_id": run_id,
                "cycle_id": cycle_id,
                "timestamp": timestamp,
                "type": event_type,
                "agent_id": agent_id,
                "trust_before": float(prev_trust),
                "trust_after": float(prev_trust),
                "authority_before": 1.0,
                "authority_after": 0.0 if status == "suppressed" else 1.0,
                "metadata": {
                    "reason": "manual_override",
                    "previous_status": prev_status,
                    "new_status": status,
                },
            }
            _emit_event(evt)

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
