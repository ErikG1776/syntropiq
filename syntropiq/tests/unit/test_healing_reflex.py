from __future__ import annotations

import pytest

from syntropiq.governance.healing_reflex import (
    compute_fs_slope,
    confidence_factor,
    rehabilitate_trust,
    should_rehabilitate,
)


def test_compute_fs_slope_windowed():
    assert compute_fs_slope([], 3) == 0.0
    assert compute_fs_slope([0.1, 0.2], 3) == 0.0
    assert compute_fs_slope([-0.2, -0.1, 0.0, 0.1], 3) == (0.1 - (-0.2)) / 3


def test_confidence_factor_clamped():
    assert confidence_factor(0.9, 0.2) == pytest.approx(0.72)
    assert confidence_factor(2.0, -1.0) == 1.0


def test_should_rehabilitate_gates(monkeypatch):
    monkeypatch.setenv("HEALING_CRISIS_MIN_CYCLES", "5")
    fs_history = [-0.4, -0.35, -0.30, -0.20, -0.10, 0.02]

    assert should_rehabilitate(
        crisis_cycles=5,
        fs_history=fs_history,
        fs_slope_window=3,
        fs_slope_min=0.01,
        posterior_mean=0.85,
        posterior_uncert=0.05,
        posterior_mean_min=0.80,
        posterior_uncert_max=0.10,
    )

    assert not should_rehabilitate(
        crisis_cycles=4,
        fs_history=fs_history,
        fs_slope_window=3,
        fs_slope_min=0.01,
        posterior_mean=0.85,
        posterior_uncert=0.05,
        posterior_mean_min=0.80,
        posterior_uncert_max=0.10,
    )

    assert not should_rehabilitate(
        crisis_cycles=5,
        fs_history=[-0.2, -0.22, -0.25, -0.30, -0.32, -0.35],
        fs_slope_window=3,
        fs_slope_min=0.01,
        posterior_mean=0.85,
        posterior_uncert=0.05,
        posterior_mean_min=0.80,
        posterior_uncert_max=0.10,
    )


def test_rehabilitate_trust_bounded():
    assert rehabilitate_trust(0.65, 0.02, 0.70) == 0.67
    assert rehabilitate_trust(0.69, 0.02, 0.70) == 0.70
    assert rehabilitate_trust(0.99, 0.10, 1.20) == 1.0
