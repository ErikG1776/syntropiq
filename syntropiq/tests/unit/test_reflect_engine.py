import pytest

from syntropiq.reflect.engine import run_reflect


def _base_kwargs():
    return {
        "run_id": "RUN_REF",
        "cycle_id": "RUN_REF:1",
        "timestamp": "2026-02-28T12:00:00Z",
        "trust_by_agent": {"a": 0.9, "b": 0.8},
        "thresholds": {
            "trust_threshold": 0.7,
            "suppression_threshold": 0.75,
            "drift_delta": 0.1,
        },
        "suppression_active": False,
        "recent_cycles": [
            {"trust_delta_total": 0.02, "successes": 3, "failures": 1},
            {"trust_delta_total": 0.01, "successes": 4, "failures": 0},
        ],
        "recent_events": [],
        "horizon_steps": 5,
        "theta": 0.10,
        "weights_decay": 0.85,
        "mode": "score",
        "latest_replay_score": 1.0,
    }


def test_reflect_deterministic_and_bounded():
    kwargs = _base_kwargs()
    d1 = run_reflect(**kwargs)
    d2 = run_reflect(**kwargs)

    assert d1.Fs == pytest.approx(d2.Fs)
    assert -1.0 <= d1.Fs <= 1.0

    total_weight = sum(d1.weights.values())
    assert total_weight == pytest.approx(1.0)

    for p in d1.penalties:
        assert 0.0 <= p.penalty <= 1.0


def test_reflect_classification_states():
    stable = run_reflect(**_base_kwargs())
    assert stable.classification in {"stable", "degrading", "crisis"}

    degraded_kwargs = _base_kwargs()
    degraded_kwargs["trust_by_agent"] = {"a": 0.45, "b": 0.40}
    degraded_kwargs["suppression_active"] = True
    degraded_kwargs["latest_replay_score"] = 0.5
    degraded_kwargs["theta"] = 0.2
    degraded = run_reflect(**degraded_kwargs)

    assert degraded.classification in {"degrading", "crisis"}
    assert degraded.Fs <= stable.Fs
