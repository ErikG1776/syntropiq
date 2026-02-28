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
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from syntropiq.core.context import get_request_id
from syntropiq.core.invariants import (
    InvariantViolation,
    Invariants,
    emit_violations,
    mode_from_env,
)
from syntropiq.core.replay import compare_runs, compute_r, load_run_artifacts, replay_run
from syntropiq.core.models import Task
from syntropiq.optimize.bayes_posterior import posterior_from_cycles
from syntropiq.optimize.config import (
    get_bayes_mode,
    get_current_lambda,
    get_default_lambda_vector,
    get_lambda_adapt_mode,
    get_optimize_mode,
    set_current_lambda,
)
from syntropiq.optimize.lambda_adaptation import compute_adaptive_lambda
from syntropiq.optimize.lambda_optimizer import optimize_tasks
from syntropiq.optimize.schema import LambdaVector, OptimizeInput
from syntropiq.reflect.config import get_reflect_consensus_mode, get_reflect_mode
from syntropiq.reflect.consensus import PerspectiveProfile, run_consensus_reflect
from syntropiq.reflect.engine import run_reflect
from syntropiq.api.schemas import (
    ActorSchema,
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


def _emit_invariant_alerts(violations: list[InvariantViolation], base_metadata: Optional[dict] = None) -> None:
    if not violations:
        return
    if mode_from_env() == "off":
        return
    if server.telemetry_hub is None:
        return
    emit_violations(server.telemetry_hub, violations, base_metadata=base_metadata)


def _actor_dict(actor: Optional[ActorSchema | dict]) -> Optional[dict]:
    if actor is None:
        return None
    if hasattr(actor, "model_dump"):
        data = actor.model_dump()
    elif isinstance(actor, dict):
        data = dict(actor)
    else:
        return None

    user_id = data.get("user_id")
    role = data.get("role")
    source = data.get("source") or "control-plane"
    if not isinstance(user_id, str) or not isinstance(role, str):
        return None
    return {"user_id": user_id, "role": role, "source": source}


def _with_actor_metadata(metadata: Optional[dict], actor: Optional[ActorSchema | dict]) -> dict:
    merged = dict(metadata or {})
    actor_payload = _actor_dict(actor)
    if actor_payload is not None:
        merged["actor"] = actor_payload
    return merged


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

    cooldown_violations = Invariants.check_cooldown_bound(CIRCUIT_STATE.get("cooldown_cycles"))
    _emit_invariant_alerts(
        cooldown_violations,
        {
            "run_id": run_id,
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "request_id": get_request_id(),
            "component": "circuit_breaker",
            "reason": reason,
        },
    )

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
    actor: Optional[ActorSchema] = None


class UpdateAgentStatusRequest(BaseModel):
    agent_id: str
    status: str
    actor: Optional[ActorSchema] = None


class ReplayValidateRequest(BaseModel):
    run_id: str
    threshold: float = 0.99
    seed: Optional[int] = None
    mode: str = "light"
    actor: Optional[ActorSchema] = None


class OptimizeScoreRequest(BaseModel):
    run_id: str = "OPT_RUN"
    tasks: List[TaskSchema]
    lambda_values: Optional[Dict[str, float]] = Field(default=None, alias="lambda")
    context: Dict[str, Any] = Field(default_factory=dict)
    trust_by_agent: Optional[Dict[str, float]] = None
    actor: Optional[ActorSchema] = None


class ReflectRunRequest(BaseModel):
    run_id: str
    cycle_id: str
    horizon_steps: int = 5
    theta: float = 0.10
    weights_decay: float = 0.85
    actor: Optional[ActorSchema] = None


class OptimizeLambdaRequest(BaseModel):
    run_id: str = "GLOBAL"
    signals: Dict[str, Any] = Field(default_factory=dict)
    base_lambda: Optional[Dict[str, float]] = Field(default=None, alias="base_lambda")


class ReflectConsensusRequest(BaseModel):
    run_id: str
    cycle_id: str
    horizon_steps: int = 5
    theta: float = 0.10
    profiles: Optional[List[Dict[str, Any]]] = None
    actor: Optional[ActorSchema] = None


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
    actor = _actor_dict(request.actor)
    task_obj = Task(
        id=request.task.id,
        impact=request.task.impact,
        urgency=request.task.urgency,
        risk=request.task.risk,
        metadata=request.task.metadata or {},
    )

    run_id = request.run_id or "EXEC_GATEWAY"

    request_id = get_request_id()
    start_violations = []
    start_violations.extend(Invariants.check_request_id_present(request_id))
    tau_value = (
        float(getattr(server.mutation_engine, "trust_threshold", 0.0))
        if server.mutation_engine is not None
        else None
    )
    start_violations.extend(Invariants.check_tau_range(tau_value) if tau_value is not None else [])
    _emit_invariant_alerts(
        start_violations,
        {
            "run_id": run_id,
            "cycle_id": f"{run_id}:execute:start",
            "timestamp": _utc_ts(),
            "request_id": request_id,
            "component": "governance_execute",
            "actor": actor,
        },
    )

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

    selection_violations = []
    if not strategy_name:
        selection_violations.append(
            InvariantViolation(
                name="strategy_present",
                severity="warn",
                expected="non-empty strategy",
                actual=str(strategy_name),
                context={"strategy": strategy_name},
            )
        )
    if len(selected_ids) == 0:
        selection_violations.append(
            InvariantViolation(
                name="selected_agents_non_empty",
                severity="warn",
                expected="selected_agents length > 0 on success path",
                actual="0",
                context={"strategy": strategy_name, "eligible": list(eligible_agent_map.keys())},
            )
        )
    _emit_invariant_alerts(
        selection_violations,
        {
            "run_id": run_id,
            "cycle_id": f"{run_id}:execute:selection",
            "timestamp": _utc_ts(),
            "request_id": request_id,
            "component": "governance_execute",
            "actor": actor,
        },
    )

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
        "metadata": _with_actor_metadata(
            {
                **(mediation_metadata or {}),
                "task_id": getattr(request.task, "id", None),
            },
            actor,
        ),
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
                    "metadata": _with_actor_metadata(dict(result.get("mutation", {})), actor),
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


def _apply_agent_status_update(agent_id: str, status: str, actor: Optional[ActorSchema | dict] = None):
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
                "metadata": _with_actor_metadata(
                    {
                        "reason": "manual_override",
                        "previous_status": prev_status,
                        "new_status": status,
                    },
                    actor,
                ),
            }
            _emit_event(evt)

        return {"agent_id": agent_id, "new_status": status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/agents/{agent_id}/status")
def update_agent_status(agent_id: str, status: str):
    return _apply_agent_status_update(agent_id=agent_id, status=status, actor=None)


@router.put("/agents/status")
def update_agent_status_body(request: UpdateAgentStatusRequest):
    return _apply_agent_status_update(
        agent_id=request.agent_id,
        status=request.status,
        actor=request.actor,
    )


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


@router.get("/metrics")
def get_metrics():
    if server.telemetry_hub is None:
        return {
            "execute_calls": 0,
            "suppression_events": 0,
            "circuit_trips": 0,
        }
    return server.telemetry_hub.metrics()


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


@router.get("/audit/verify")
def verify_audit_chain(chain_id: str = Query(default="GLOBAL")):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        return {
            "chain_id": chain_id,
            "events": {"ok": True, "checked": 0, "first_bad_index": None, "reason": "telemetry_state_unavailable"},
            "cycles": {"ok": True, "checked": 0, "first_bad_index": None, "reason": "telemetry_state_unavailable"},
        }

    return {
        "chain_id": chain_id,
        "events": manager.verify_events_chain(chain_id=chain_id),
        "cycles": manager.verify_cycles_chain(chain_id=chain_id),
    }


@router.post("/replay/validate")
def replay_validate(request: ReplayValidateRequest):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    mode = request.mode if request.mode in {"light", "full"} else "light"
    threshold = float(request.threshold)
    actor = _actor_dict(request.actor)
    request_id = get_request_id()

    artifacts = load_run_artifacts(manager, request.run_id)
    if not artifacts.get("cycles"):
        raise HTTPException(status_code=404, detail="run_artifacts_not_found")

    replayed = replay_run(artifacts, seed=request.seed, mode=mode)
    comparison = compare_runs(artifacts, replayed)
    r_score = compute_r(comparison)
    ok = r_score >= threshold

    component_scores = {
        "selection_match": comparison.selection_match,
        "trust_corr": comparison.trust_corr,
        "threshold_corr": comparison.threshold_corr,
        "suppression_match": comparison.suppression_match,
    }
    details = {
        "diagnostics": comparison.diagnostics,
        "mode_requested": request.mode,
        "mode_used": replayed.get("mode", mode),
        "explanation": replayed.get("explanation"),
        "request_id": request_id,
    }
    if actor is not None:
        details["actor"] = actor

    persisted = manager.save_replay_validation(
        {
            "run_id": request.run_id,
            "r_score": r_score,
            "component_scores": component_scores,
            "ok": ok,
            "threshold": threshold,
            "details": details,
        }
    )

    return {
        "ok": ok,
        "run_id": request.run_id,
        "r_score": r_score,
        "threshold": threshold,
        "components": component_scores,
        "diagnostics": comparison.diagnostics,
        "mode": replayed.get("mode", mode),
        "explanation": replayed.get("explanation"),
        "validation_id": persisted.get("id"),
        "request_id": request_id,
        "actor": actor,
    }


@router.post("/optimize/score")
def optimize_score(request: OptimizeScoreRequest):
    mode = get_optimize_mode()
    if mode not in {"score", "integrate"}:
        raise HTTPException(status_code=403, detail="optimize_disabled")

    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    request_id = get_request_id()
    actor = _actor_dict(request.actor)

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

    if request.trust_by_agent:
        trust_by_agent = {str(k): float(v) for k, v in request.trust_by_agent.items()}
    else:
        trust_by_agent = {}
        if getattr(server, "agent_registry", None) is not None:
            agents = server.agent_registry.get_agents_dict()
            trust_by_agent = {
                aid: float(getattr(agent, "trust_score", 0.0))
                for aid, agent in agents.items()
                if getattr(agent, "status", "active") != "suppressed"
            }

    if request.lambda_values:
        lam = LambdaVector(
            l_cost=float(request.lambda_values.get("l_cost", 0.25)),
            l_time=float(request.lambda_values.get("l_time", 0.25)),
            l_risk=float(request.lambda_values.get("l_risk", 0.25)),
            l_trust=float(request.lambda_values.get("l_trust", 0.25)),
        ).enforce_bounds().normalize()
    else:
        lam = get_current_lambda(request.run_id)

    context = {"V_prime": dict(request.context or {})}

    optimize_input = OptimizeInput(
        tasks=tasks,
        trust_by_agent=trust_by_agent,
        context=context,
        actor=actor,
        request_id=request_id,
    )
    decision = optimize_tasks(
        input=optimize_input,
        lambda_vector=lam,
        run_id=request.run_id,
    )
    persisted = manager.save_optimization_event(decision.to_dict())

    adapt_mode = get_lambda_adapt_mode()
    bayes_mode = get_bayes_mode()
    adaptation_payload = None
    posterior_payload = None

    if adapt_mode in {"log", "apply"}:
        recent_cycles = manager.load_cycles_by_run_id(request.run_id, limit=50)
        success_total = sum(int(c.get("successes", 0)) for c in recent_cycles[-10:])
        fail_total = sum(int(c.get("failures", 0)) for c in recent_cycles[-10:])
        denom = success_total + fail_total
        failure_rate = (fail_total / denom) if denom > 0 else 0.0

        bayes_multiplier = 1.0
        if bayes_mode in {"log", "apply"}:
            posterior_payload = posterior_from_cycles(recent_cycles[-50:])
            manager.save_bayes_posterior(
                {
                    "run_id": request.run_id,
                    **posterior_payload,
                }
            )
            if bayes_mode == "apply":
                bayes_multiplier = float(posterior_payload.get("suggested_risk_multiplier", 1.0))

        avg_trust = (
            sum(float(v) for v in trust_by_agent.values()) / len(trust_by_agent)
            if trust_by_agent
            else 0.0
        )
        suppression_active = any(float(v) < float(getattr(server.mutation_engine, "suppression_threshold", 0.75)) for v in trust_by_agent.values())
        replay_rows = manager.load_replay_validations(request.run_id, limit=1)
        r_latest = float(replay_rows[0]["r_score"]) if replay_rows else None

        signals = {
            "avg_trust": avg_trust,
            "suppression_active": suppression_active,
            "drift_delta": float(getattr(server.mutation_engine, "drift_delta", 0.1)),
            "r_score_latest": r_latest,
            "A_score": float(decision.alignment_score),
            "failure_rate": failure_rate,
            "bayes_risk_multiplier": bayes_multiplier,
        }
        recommended, deltas = compute_adaptive_lambda(
            base=lam,
            signals=signals,
            bounds={"max_step": 0.02, "max_trust": 0.3},
        )
        adaptation_payload = {
            "old_lambda": lam.as_dict(),
            "new_lambda": recommended.as_dict(),
            "deltas": deltas,
            "signals": signals,
            "mode": adapt_mode,
        }
        manager.save_lambda_history(
            {
                "run_id": request.run_id,
                **adaptation_payload,
            }
        )
        if adapt_mode == "apply":
            set_current_lambda(recommended, run_id=request.run_id)

    response = dict(persisted)
    if adaptation_payload is not None:
        response["lambda_adaptation"] = adaptation_payload
    if posterior_payload is not None:
        response["bayes_posterior"] = posterior_payload
    return response


@router.post("/optimize/lambda/recommend")
def optimize_lambda_recommend(request: OptimizeLambdaRequest):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    if request.base_lambda:
        base = LambdaVector(
            l_cost=float(request.base_lambda.get("l_cost", 0.25)),
            l_time=float(request.base_lambda.get("l_time", 0.25)),
            l_risk=float(request.base_lambda.get("l_risk", 0.25)),
            l_trust=float(request.base_lambda.get("l_trust", 0.25)),
        ).enforce_bounds().normalize()
    else:
        base = get_current_lambda(request.run_id)

    recommended, deltas = compute_adaptive_lambda(
        base=base,
        signals=dict(request.signals or {}),
        bounds={"max_step": 0.02, "max_trust": 0.3},
    )
    payload = {
        "run_id": request.run_id,
        "old_lambda": base.as_dict(),
        "new_lambda": recommended.as_dict(),
        "deltas": deltas,
        "signals": dict(request.signals or {}),
        "mode": "recommend",
    }
    manager.save_lambda_history(payload)
    return payload


@router.post("/optimize/lambda/apply")
def optimize_lambda_apply(request: OptimizeLambdaRequest):
    if get_lambda_adapt_mode() != "apply":
        raise HTTPException(status_code=403, detail="lambda_apply_disabled")

    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    base = get_current_lambda(request.run_id)
    if request.base_lambda:
        base = LambdaVector(
            l_cost=float(request.base_lambda.get("l_cost", 0.25)),
            l_time=float(request.base_lambda.get("l_time", 0.25)),
            l_risk=float(request.base_lambda.get("l_risk", 0.25)),
            l_trust=float(request.base_lambda.get("l_trust", 0.25)),
        ).enforce_bounds().normalize()

    recommended, deltas = compute_adaptive_lambda(
        base=base,
        signals=dict(request.signals or {}),
        bounds={"max_step": 0.02, "max_trust": 0.3},
    )
    set_current_lambda(recommended, run_id=request.run_id)
    payload = {
        "run_id": request.run_id,
        "old_lambda": base.as_dict(),
        "new_lambda": recommended.as_dict(),
        "deltas": deltas,
        "signals": dict(request.signals or {}),
        "mode": "apply",
    }
    manager.save_lambda_history(payload)
    return payload


@router.get("/optimize/lambda/history")
def optimize_lambda_history(run_id: str = Query(...), limit: int = Query(default=50, ge=1, le=500)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.load_lambda_history(run_id=run_id, limit=limit)


@router.get("/optimize/lambda/verify")
def optimize_lambda_verify(run_id: str = Query(...), limit: int = Query(default=200, ge=1, le=2000)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.verify_lambda_chain(run_id=run_id, limit=limit)


@router.get("/optimize/events")
def get_optimization_events(run_id: str = Query(...), limit: int = Query(default=50, ge=1, le=500)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.load_optimization_events(run_id=run_id, limit=limit)


@router.get("/optimize/verify")
def verify_optimization_events(run_id: str = Query(...), limit: int = Query(default=200, ge=1, le=2000)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.verify_optimization_chain(run_id=run_id, limit=limit)


@router.get("/optimize/bayes")
def optimize_bayes(run_id: str = Query(...), window: int = Query(default=50, ge=1, le=500)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    cycles = manager.load_cycles_by_run_id(run_id=run_id, limit=window)
    posterior = posterior_from_cycles(cycles)
    payload = {"run_id": run_id, **posterior}
    if get_bayes_mode() in {"log", "apply"}:
        manager.save_bayes_posterior(payload)
    return payload


@router.get("/optimize/bayes/verify")
def optimize_bayes_verify(run_id: str = Query(...), limit: int = Query(default=200, ge=1, le=2000)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.verify_bayes_chain(run_id=run_id, limit=limit)


@router.post("/reflect/run")
def reflect_run(request: ReflectRunRequest):
    mode = get_reflect_mode()
    if mode not in {"score", "integrate"}:
        raise HTTPException(status_code=403, detail="reflect_disabled")

    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    actor = _actor_dict(request.actor)
    request_id = get_request_id()

    trust_by_agent: Dict[str, float] = {}
    if getattr(server, "agent_registry", None) is not None:
        agents = server.agent_registry.get_agents_dict()
        trust_by_agent = {
            aid: float(getattr(agent, "trust_score", 0.0))
            for aid, agent in agents.items()
        }

    thresholds = {
        "trust_threshold": float(getattr(server.mutation_engine, "trust_threshold", 0.7)),
        "suppression_threshold": float(getattr(server.mutation_engine, "suppression_threshold", 0.75)),
        "drift_delta": float(getattr(server.mutation_engine, "drift_delta", 0.1)),
    }

    suppression_active = False
    if getattr(server, "governance_loop", None) is not None and hasattr(server.governance_loop, "trust_engine"):
        suppressed = getattr(server.governance_loop.trust_engine, "suppressed_agents", {})
        suppression_active = bool(suppressed)

    recent_cycles = manager.load_cycles_by_run_id(request.run_id, limit=50)
    recent_events = manager.load_events_by_run_id(request.run_id, limit=200)
    if not suppression_active:
        suppression_active = any(event.get("type") == "suppression" for event in recent_events[-20:])

    latest_replay_score = None
    replay_rows = manager.load_replay_validations(request.run_id, limit=1)
    if replay_rows:
        latest_replay_score = float(replay_rows[0].get("r_score", 0.0))

    decision = run_reflect(
        run_id=request.run_id,
        cycle_id=request.cycle_id,
        timestamp=_utc_ts(),
        trust_by_agent=trust_by_agent,
        thresholds=thresholds,
        suppression_active=suppression_active,
        recent_cycles=recent_cycles,
        recent_events=recent_events,
        actor=actor,
        request_id=request_id,
        horizon_steps=request.horizon_steps,
        theta=request.theta,
        weights_decay=request.weights_decay,
        mode="integrate" if mode == "integrate" else "score",
        latest_replay_score=latest_replay_score,
    )

    persisted = manager.save_reflect_decision(decision.to_dict())
    consensus_mode = get_reflect_consensus_mode()
    if consensus_mode in {"log", "integrate"}:
        consensus = run_consensus_reflect(
            run_id=request.run_id,
            cycle_id=request.cycle_id,
            timestamp=_utc_ts(),
            trust_by_agent=trust_by_agent,
            thresholds=thresholds,
            suppression_active=suppression_active,
            recent_cycles=recent_cycles,
            recent_events=recent_events,
            actor=actor,
            request_id=request_id,
            horizon_steps=request.horizon_steps,
            theta=request.theta,
            latest_replay_score=latest_replay_score,
        )
        manager.save_consensus_insight(
            {
                "run_id": request.run_id,
                "cycle_id": request.cycle_id,
                "timestamp": _utc_ts(),
                **consensus,
                "metadata": {"actor": actor, "request_id": request_id, "mode": consensus_mode},
            }
        )
        if consensus_mode == "integrate":
            persisted = dict(persisted)
            persisted["consensus"] = consensus
    return persisted


@router.get("/reflect/decisions")
def get_reflect_decisions(run_id: str = Query(...), limit: int = Query(default=50, ge=1, le=500)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.load_reflect_decisions(run_id=run_id, limit=limit)


@router.get("/reflect/verify")
def verify_reflect_decisions(run_id: str = Query(...), limit: int = Query(default=200, ge=1, le=2000)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.verify_reflect_chain(run_id=run_id, limit=limit)


@router.post("/reflect/consensus")
def reflect_consensus(request: ReflectConsensusRequest):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")

    actor = _actor_dict(request.actor)
    request_id = get_request_id()
    trust_by_agent: Dict[str, float] = {}
    if getattr(server, "agent_registry", None) is not None:
        agents = server.agent_registry.get_agents_dict()
        trust_by_agent = {aid: float(getattr(agent, "trust_score", 0.0)) for aid, agent in agents.items()}

    thresholds = {
        "trust_threshold": float(getattr(server.mutation_engine, "trust_threshold", 0.7)),
        "suppression_threshold": float(getattr(server.mutation_engine, "suppression_threshold", 0.75)),
        "drift_delta": float(getattr(server.mutation_engine, "drift_delta", 0.1)),
    }
    suppression_active = False
    if getattr(server, "governance_loop", None) is not None and hasattr(server.governance_loop, "trust_engine"):
        suppression_active = bool(getattr(server.governance_loop.trust_engine, "suppressed_agents", {}))
    recent_cycles = manager.load_cycles_by_run_id(request.run_id, limit=50)
    recent_events = manager.load_events_by_run_id(request.run_id, limit=200)
    replay_rows = manager.load_replay_validations(request.run_id, limit=1)
    latest_replay_score = float(replay_rows[0].get("r_score", 0.0)) if replay_rows else None

    profiles = None
    if request.profiles:
        profiles = [
            PerspectiveProfile(
                name=str(item.get("name", "custom")),
                weights_decay=float(item.get("weights_decay", 0.85)),
                constraint_weight_overrides=dict(item.get("constraint_weight_overrides", {})),
                theta_override=float(item["theta_override"]) if item.get("theta_override") is not None else None,
            )
            for item in request.profiles
        ]

    consensus = run_consensus_reflect(
        run_id=request.run_id,
        cycle_id=request.cycle_id,
        timestamp=_utc_ts(),
        trust_by_agent=trust_by_agent,
        thresholds=thresholds,
        suppression_active=suppression_active,
        recent_cycles=recent_cycles,
        recent_events=recent_events,
        actor=actor,
        request_id=request_id,
        horizon_steps=request.horizon_steps,
        theta=request.theta,
        latest_replay_score=latest_replay_score,
        profiles=profiles,
    )
    persisted = manager.save_consensus_insight(
        {
            "run_id": request.run_id,
            "cycle_id": request.cycle_id,
            "timestamp": _utc_ts(),
            **consensus,
            "metadata": {"actor": actor, "request_id": request_id},
        }
    )
    return persisted


@router.get("/reflect/consensus/decisions")
def reflect_consensus_decisions(run_id: str = Query(...), limit: int = Query(default=50, ge=1, le=500)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.load_consensus_insights(run_id=run_id, limit=limit)


@router.get("/reflect/consensus/verify")
def reflect_consensus_verify(run_id: str = Query(...), limit: int = Query(default=200, ge=1, le=2000)):
    manager = getattr(server, "telemetry_state_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="telemetry_state_unavailable")
    return manager.verify_consensus_chain(run_id=run_id, limit=limit)


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
