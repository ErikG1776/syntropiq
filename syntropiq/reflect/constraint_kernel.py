from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from syntropiq.reflect.schema import ConstraintPenalty, ConstraintSpec


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalized_violation(value: float, threshold: float, direction: str) -> float:
    scale = max(abs(threshold), 1e-9)
    if direction == "max":
        violation = max(0.0, value - threshold) / scale
    else:
        violation = max(0.0, threshold - value) / scale
    return _clamp(violation, 0.0, 1.0)


def default_constraints(drift_max: float = 0.20, suppression_max: float = 0.0) -> List[ConstraintSpec]:
    return [
        ConstraintSpec(name="trust_floor", weight=0.30, threshold=0.0, direction="min", penalty_scale=1.0),
        ConstraintSpec(name="suppression_rate", weight=0.20, threshold=float(suppression_max), direction="max", penalty_scale=1.0),
        ConstraintSpec(name="drift_limit", weight=0.20, threshold=float(drift_max), direction="max", penalty_scale=1.0),
        ConstraintSpec(name="instability", weight=0.15, threshold=0.02, direction="max", penalty_scale=1.0),
        ConstraintSpec(name="reproducibility", weight=0.15, threshold=0.99, direction="min", penalty_scale=1.0),
    ]


def compute_constraint_penalties(
    trust_by_agent: Dict[str, float],
    thresholds: Dict[str, float],
    suppression_count: int,
    instability: float = 0.0,
    latest_replay_score: Optional[float] = None,
    observed_drift: float = 0.0,
    specs: Optional[List[ConstraintSpec]] = None,
) -> Tuple[List[ConstraintPenalty], float]:
    constraints = specs or default_constraints()

    trust_threshold = float(thresholds.get("trust_threshold", 0.7))
    min_trust = min([float(v) for v in trust_by_agent.values()]) if trust_by_agent else 0.0

    values = {
        "trust_floor": min_trust,
        "suppression_rate": float(suppression_count),
        "drift_limit": float(observed_drift),
        "instability": float(instability),
        "reproducibility": float(latest_replay_score) if latest_replay_score is not None else 1.0,
    }

    penalties: List[ConstraintPenalty] = []
    total = 0.0

    for spec in constraints:
        threshold = trust_threshold if spec.name == "trust_floor" else spec.threshold
        value = float(values.get(spec.name, 0.0))

        if spec.name == "reproducibility" and latest_replay_score is None:
            penalty = 0.0
        else:
            violation = _normalized_violation(value, threshold, spec.direction)
            penalty = _clamp(spec.weight * spec.penalty_scale * violation, 0.0, 1.0)

        penalties.append(
            ConstraintPenalty(
                name=spec.name,
                value=value,
                threshold=float(threshold),
                penalty=penalty,
                weight=float(spec.weight),
            )
        )
        total += penalty

    total_penalty = _clamp(total, 0.0, 1.0)
    return penalties, total_penalty
