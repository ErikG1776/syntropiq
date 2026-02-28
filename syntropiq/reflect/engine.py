from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from syntropiq.reflect.constraint_kernel import compute_constraint_penalties
from syntropiq.reflect.foresight import estimate_expected_delta, project_horizon
from syntropiq.reflect.fs_score import compute_fs_from_projections, compute_weights
from syntropiq.reflect.schema import ConstraintSpec, ReflectDecision


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_failure_rate(recent_cycles: Optional[List[Dict[str, Any]]]) -> float:
    if not recent_cycles:
        return 0.0
    total_success = 0
    total_fail = 0
    for cycle in recent_cycles[-5:]:
        total_success += int(cycle.get("successes", 0))
        total_fail += int(cycle.get("failures", 0))
    denom = total_success + total_fail
    if denom <= 0:
        return 0.0
    return total_fail / denom


def _infer_instability(recent_events: Optional[List[Dict[str, Any]]], thresholds: Dict[str, float]) -> float:
    if not recent_events:
        return 0.0

    latest_mutation = None
    for event in reversed(recent_events):
        if event.get("type") == "mutation":
            latest_mutation = event.get("metadata") or {}
            break
    if latest_mutation is None:
        return 0.0

    trust_before = float(thresholds.get("trust_threshold", 0.0))
    trust_after = float(latest_mutation.get("trust_threshold", trust_before))
    return abs(trust_after - trust_before)


def run_reflect(
    run_id: str,
    cycle_id: str,
    timestamp: Optional[str],
    trust_by_agent: Dict[str, float],
    thresholds: Dict[str, float],
    suppression_active: bool,
    recent_cycles: Optional[List[Dict[str, Any]]] = None,
    recent_events: Optional[List[Dict[str, Any]]] = None,
    actor: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    horizon_steps: int = 5,
    theta: float = 0.10,
    weights_decay: float = 0.85,
    mode: str = "score",
    latest_replay_score: Optional[float] = None,
    constraint_specs: Optional[List[ConstraintSpec]] = None,
) -> ReflectDecision:
    horizon_steps = max(1, int(horizon_steps))
    theta = float(theta)
    weights = compute_weights(horizon_steps, decay=float(weights_decay))

    expected_delta = estimate_expected_delta(recent_cycles or [], agent_count=max(1, len(trust_by_agent)))
    projections = project_horizon(
        trust_by_agent=trust_by_agent,
        horizon_steps=horizon_steps,
        expected_delta=expected_delta,
        suppression_active=suppression_active,
    )

    failure_rate = _infer_failure_rate(recent_cycles)
    Fs_raw, foresight_steps = compute_fs_from_projections(
        projections=projections,
        weights=weights,
        thresholds=thresholds,
        suppression_active=suppression_active,
        failure_rate=failure_rate,
    )

    suppression_count = 1 if suppression_active else 0
    instability = _infer_instability(recent_events, thresholds)
    penalties, total_penalty = compute_constraint_penalties(
        trust_by_agent=trust_by_agent,
        thresholds=thresholds,
        suppression_count=suppression_count,
        instability=instability,
        latest_replay_score=latest_replay_score,
        specs=constraint_specs,
    )

    Fs = max(-1.0, min(1.0, Fs_raw - total_penalty))

    margin = 0.10
    if Fs >= theta:
        classification = "stable"
        action = "hold"
    elif Fs >= (theta - margin):
        classification = "degrading"
        action = "tighten"
    else:
        classification = "crisis"
        action = "tighten"

    advisory = {
        "recommended_action": action,
        "recommended_deltas": {
            "trust_threshold": 0.01 if action == "tighten" else 0.0,
            "suppression_threshold": 0.01 if action == "tighten" else 0.0,
            "drift_delta": 0.0,
        },
        "non_binding": True,
    }

    metadata = {
        "source": "reflect_engine",
        "request_id": request_id,
        "actor": actor,
        "total_penalty": total_penalty,
        "Fs_raw": Fs_raw,
        "expected_delta": expected_delta,
    }

    decision = ReflectDecision.new(
        run_id=run_id,
        cycle_id=cycle_id,
        mode="integrate" if mode == "integrate" else "score",
        horizon_steps=horizon_steps,
        weights=weights,
        Fs=Fs,
        Fs_threshold=theta,
        classification=classification,
        penalties=penalties,
        foresight=foresight_steps,
        advisory=advisory,
        metadata=metadata,
    )

    if timestamp:
        decision.timestamp = timestamp
    else:
        decision.timestamp = _utc_now()

    return decision
