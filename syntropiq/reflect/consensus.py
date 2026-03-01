from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import median
from typing import Any, Dict, List, Optional

from syntropiq.reflect.constraint_kernel import default_constraints
from syntropiq.reflect.engine import run_reflect


@dataclass
class PerspectiveProfile:
    name: str
    weights_decay: float
    constraint_weight_overrides: Dict[str, float]
    theta_override: Optional[float] = None


def default_perspectives() -> List[PerspectiveProfile]:
    return [
        PerspectiveProfile(
            name="safety",
            weights_decay=0.92,
            constraint_weight_overrides={"trust_floor": 0.35, "reproducibility": 0.20},
            theta_override=0.15,
        ),
        PerspectiveProfile(
            name="efficiency",
            weights_decay=0.75,
            constraint_weight_overrides={"suppression_rate": 0.15, "instability": 0.10},
            theta_override=0.05,
        ),
        PerspectiveProfile(
            name="balanced",
            weights_decay=0.85,
            constraint_weight_overrides={},
            theta_override=None,
        ),
    ]


def run_consensus_reflect(
    run_id: str,
    cycle_id: str,
    timestamp: str,
    trust_by_agent: Dict[str, float],
    thresholds: Dict[str, float],
    suppression_active: bool,
    recent_cycles: Optional[List[Dict[str, Any]]] = None,
    recent_events: Optional[List[Dict[str, Any]]] = None,
    actor: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    horizon_steps: int = 5,
    theta: float = 0.10,
    latest_replay_score: Optional[float] = None,
    profiles: Optional[List[PerspectiveProfile]] = None,
) -> Dict[str, Any]:
    profile_set = profiles or default_perspectives()
    base_specs = default_constraints()

    per_profile = []
    fs_values = []

    for profile in profile_set:
        specs = []
        for spec in base_specs:
            weight = profile.constraint_weight_overrides.get(spec.name, spec.weight)
            cloned = type(spec)(
                name=spec.name,
                weight=float(weight),
                threshold=float(spec.threshold),
                direction=spec.direction,
                penalty_scale=float(spec.penalty_scale),
            )
            specs.append(cloned)

        decision = run_reflect(
            run_id=run_id,
            cycle_id=cycle_id,
            timestamp=timestamp,
            trust_by_agent=trust_by_agent,
            thresholds=thresholds,
            suppression_active=suppression_active,
            recent_cycles=recent_cycles,
            recent_events=recent_events,
            actor=actor,
            request_id=request_id,
            horizon_steps=horizon_steps,
            theta=profile.theta_override if profile.theta_override is not None else theta,
            weights_decay=profile.weights_decay,
            mode="score",
            latest_replay_score=latest_replay_score,
            constraint_specs=specs,
        )
        fs_values.append(float(decision.Fs))
        per_profile.append({"name": profile.name, "Fs": float(decision.Fs), "classification": decision.classification})

    consensus_fs = float(median(fs_values)) if fs_values else 0.0
    if fs_values:
        abs_dev = [abs(v - consensus_fs) for v in fs_values]
        disagreement = float(median(abs_dev))
    else:
        disagreement = 0.0

    outliers = [
        item["name"]
        for item in per_profile
        if abs(float(item["Fs"]) - consensus_fs) > max(0.10, 2.0 * disagreement)
    ]

    return {
        "consensus_Fs": consensus_fs,
        "disagreement": disagreement,
        "profiles": per_profile,
        "outliers": outliers,
        "profile_specs": [asdict(p) for p in profile_set],
    }
