from __future__ import annotations

from typing import Dict, Tuple

from syntropiq.optimize.schema import LambdaVector


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_adaptive_lambda(base: LambdaVector, signals: dict, bounds: dict) -> Tuple[LambdaVector, Dict[str, float]]:
    max_step = float(bounds.get("max_step", 0.02))
    max_trust = bounds.get("max_trust", 0.3)

    avg_trust = float(signals.get("avg_trust", 0.0))
    suppression_active = bool(signals.get("suppression_active", False))
    drift_delta = float(signals.get("drift_delta", 0.0))
    r_score_latest = signals.get("r_score_latest")
    r_score = float(r_score_latest) if r_score_latest is not None else None
    a_score = float(signals.get("A_score", 50.0))
    failure_rate = float(signals.get("failure_rate", 0.0))
    bayes_risk_multiplier = float(signals.get("bayes_risk_multiplier", 1.0))

    proposed = {
        "l_cost": 0.0,
        "l_time": 0.0,
        "l_risk": 0.0,
        "l_trust": 0.0,
    }

    if suppression_active:
        proposed["l_risk"] += 0.015
        proposed["l_trust"] -= 0.010

    if drift_delta >= 0.12:
        proposed["l_risk"] += 0.015
        proposed["l_time"] += 0.010

    if avg_trust >= 0.80 and (r_score is None or r_score >= 0.99):
        proposed["l_trust"] += 0.010
        proposed["l_risk"] -= 0.005

    if a_score < 60.0:
        proposed["l_trust"] += 0.010
        proposed["l_risk"] += 0.010

    if failure_rate > 0.20:
        proposed["l_risk"] += 0.010
        proposed["l_cost"] -= 0.005

    # Bayesian posterior can increase conservative risk weight.
    if bayes_risk_multiplier > 1.0:
        proposed["l_risk"] += min(max_step, 0.01 * (bayes_risk_multiplier - 1.0))

    deltas = {
        key: _clamp(value, -max_step, max_step)
        for key, value in proposed.items()
    }

    updated = LambdaVector(
        l_cost=base.l_cost + deltas["l_cost"],
        l_time=base.l_time + deltas["l_time"],
        l_risk=base.l_risk + deltas["l_risk"],
        l_trust=base.l_trust + deltas["l_trust"],
    )
    updated.enforce_bounds(max_trust=max_trust).normalize()

    return updated, deltas
