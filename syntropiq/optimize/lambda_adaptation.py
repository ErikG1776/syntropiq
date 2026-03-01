from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from syntropiq.optimize.schema import LambdaVector


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class _AdaptationState:
    crisis_cycles: int = 0
    stable_cycles: int = 0
    recovery_active: bool = False


_STATE_BY_RUN: Dict[str, _AdaptationState] = {}


def _get_state(run_key: str) -> _AdaptationState:
    state = _STATE_BY_RUN.get(run_key)
    if state is None:
        state = _AdaptationState()
        _STATE_BY_RUN[run_key] = state
    return state


def compute_adaptive_lambda(base: LambdaVector, signals: dict, bounds: dict) -> Tuple[LambdaVector, Dict[str, float]]:
    max_step = float(bounds.get("max_step", 0.02))
    max_trust = bounds.get("max_trust", 0.3)
    min_lambda_bound = float(bounds.get("min_lambda_bound", 0.0))
    max_lambda_bound = float(bounds.get("max_lambda_bound", 1.0))
    recovery_step = min(max_step, float(bounds.get("recovery_step", max_step)))

    avg_trust = float(signals.get("avg_trust", 0.0))
    suppression_active = bool(signals.get("suppression_active", False))
    drift_delta = float(signals.get("drift_delta", 0.0))
    r_score_latest = signals.get("r_score_latest")
    r_score = float(r_score_latest) if r_score_latest is not None else None
    a_score = float(signals.get("A_score", 50.0))
    failure_rate = float(signals.get("failure_rate", 0.0))
    bayes_risk_multiplier = float(signals.get("bayes_risk_multiplier", 1.0))
    reflect_classification = str(signals.get("reflect_classification", "")).lower()
    fs_score = signals.get("Fs")
    fs_threshold = signals.get("fs_threshold")
    run_key = str(signals.get("run_id") or "GLOBAL")

    state = _get_state(run_key)
    if fs_score is not None and fs_threshold is not None:
        if float(fs_score) < float(fs_threshold):
            state.crisis_cycles += 1
            state.stable_cycles = 0
        else:
            state.crisis_cycles = 0
            state.stable_cycles += 1

        if state.crisis_cycles >= 3 and suppression_active:
            state.recovery_active = True
        if state.stable_cycles >= 5:
            state.recovery_active = False

    proposed = {
        "l_cost": 0.0,
        "l_time": 0.0,
        "l_risk": 0.0,
        "l_trust": 0.0,
    }

    # Crisis override logic: deterministic recovery reflex, bounded and replayable.
    if state.recovery_active and suppression_active and reflect_classification == "crisis":
        l_risk_new = max(base.l_risk - recovery_step, min_lambda_bound)
        l_trust_new = min(base.l_trust + recovery_step, max_lambda_bound)
        l_trust_new = min(l_trust_new, max_trust if max_trust is not None else l_trust_new)

        remaining = max(0.0, 1.0 - l_risk_new - l_trust_new)
        prev_remaining = max(1e-12, base.l_cost + base.l_time)
        l_cost_new = remaining * (base.l_cost / prev_remaining)
        l_time_new = remaining * (base.l_time / prev_remaining)

        updated = LambdaVector(
            l_cost=l_cost_new,
            l_time=l_time_new,
            l_risk=l_risk_new,
            l_trust=l_trust_new,
        ).enforce_bounds(min_value=min_lambda_bound, max_value=max_lambda_bound, max_trust=max_trust).normalize()

        deltas = {
            "l_cost": _clamp(updated.l_cost - base.l_cost, -max_step, max_step),
            "l_time": _clamp(updated.l_time - base.l_time, -max_step, max_step),
            "l_risk": _clamp(updated.l_risk - base.l_risk, -max_step, max_step),
            "l_trust": _clamp(updated.l_trust - base.l_trust, -max_step, max_step),
        }
        return updated, deltas

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
    updated.enforce_bounds(min_value=min_lambda_bound, max_value=max_lambda_bound, max_trust=max_trust).normalize()

    return updated, deltas
