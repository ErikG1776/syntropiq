from __future__ import annotations

import os
from typing import List


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_fs_slope(fs_history: List[float], window: int) -> float:
    if window <= 0:
        return 0.0
    if len(fs_history) < (window + 1):
        return 0.0
    return (float(fs_history[-1]) - float(fs_history[-(window + 1)])) / float(window)


def confidence_factor(mean: float, uncertainty: float) -> float:
    mean_clamped = _clamp(float(mean), 0.0, 1.0)
    uncertainty_clamped = _clamp(float(uncertainty), 0.0, 1.0)
    return mean_clamped * (1.0 - uncertainty_clamped)


def should_rehabilitate(
    *,
    crisis_cycles: int,
    fs_history: List[float],
    fs_slope_window: int,
    fs_slope_min: float,
    posterior_mean: float,
    posterior_uncert: float,
    posterior_mean_min: float,
    posterior_uncert_max: float,
) -> bool:
    crisis_min = int(os.getenv("HEALING_CRISIS_MIN_CYCLES", "5"))
    if int(crisis_cycles) < int(crisis_min):
        return False

    slope = compute_fs_slope(fs_history, fs_slope_window)
    if slope < float(fs_slope_min):
        return False
    if float(posterior_mean) < float(posterior_mean_min):
        return False
    if float(posterior_uncert) > float(posterior_uncert_max):
        return False
    return True


def rehabilitate_trust(current: float, step: float, cap: float) -> float:
    new_value = min(float(cap), float(current) + float(step))
    return _clamp(new_value, 0.0, 1.0)
