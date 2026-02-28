from __future__ import annotations

from typing import Dict, List, Tuple

from syntropiq.reflect.schema import ForesightStep


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_weights(horizon_steps: int, decay: float = 0.85) -> Dict[str, float]:
    steps = max(1, horizon_steps)
    raw = [float(decay) ** i for i in range(steps)]
    total = sum(raw)
    if total <= 0:
        return {str(i): 1.0 / steps for i in range(steps)}
    return {str(i): raw[i] / total for i in range(steps)}


def compute_fs_from_projections(
    projections: List[Dict[str, float]],
    weights: Dict[str, float],
    thresholds: Dict[str, float],
    suppression_active: bool,
    failure_rate: float = 0.0,
) -> Tuple[float, List[ForesightStep]]:
    if not projections:
        return 0.0, []

    drift_proxy = _clamp(float(thresholds.get("drift_delta", 0.1)) / 0.2, 0.0, 1.0)
    risk_proxy = max(drift_proxy, _clamp(float(failure_rate), 0.0, 1.0))

    steps: List[ForesightStep] = []
    prev_avg = None
    fs_total = 0.0

    for idx, trust_vector in enumerate(projections):
        if trust_vector:
            avg_trust = sum(trust_vector.values()) / len(trust_vector)
        else:
            avg_trust = 0.0

        A = _clamp(avg_trust - risk_proxy, 0.0, 1.0)
        delta = abs(avg_trust - prev_avg) if prev_avg is not None else 0.0
        suppression_indicator = 0.2 if suppression_active else 0.0
        D = _clamp(delta + suppression_indicator, 0.0, 1.0)

        w = float(weights.get(str(idx), 0.0))
        weighted = w * (A - D)
        fs_total += weighted

        steps.append(
            ForesightStep(
                horizon_index=idx,
                A=A,
                D=D,
                weighted=weighted,
                notes={
                    "avg_trust": avg_trust,
                    "risk_proxy": risk_proxy,
                    "suppression_indicator": suppression_indicator,
                },
            )
        )

        prev_avg = avg_trust

    Fs = _clamp(fs_total, -1.0, 1.0)
    return Fs, steps
