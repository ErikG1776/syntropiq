from __future__ import annotations

from typing import Dict, List


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_expected_delta(recent_cycles: List[Dict], agent_count: int) -> float:
    if not recent_cycles or agent_count <= 0:
        return 0.0

    deltas = []
    for cycle in recent_cycles[-5:]:
        delta_total = cycle.get("trust_delta_total")
        if delta_total is None:
            continue
        deltas.append(float(delta_total) / max(agent_count, 1))

    if not deltas:
        return 0.0
    return sum(deltas) / len(deltas)


def project_horizon(
    trust_by_agent: Dict[str, float],
    horizon_steps: int,
    expected_delta: float,
    suppression_active: bool,
) -> List[Dict[str, float]]:
    current = {aid: float(v) for aid, v in trust_by_agent.items()}
    projections: List[Dict[str, float]] = []

    suppression_adjustment = -0.01 if suppression_active else 0.0
    step_delta = expected_delta + suppression_adjustment

    for _ in range(max(0, horizon_steps)):
        current = {
            aid: _clamp(value + step_delta, 0.0, 1.0)
            for aid, value in current.items()
        }
        projections.append(dict(current))

    return projections
