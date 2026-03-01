import pytest

from syntropiq.optimize.lambda_adaptation import compute_adaptive_lambda
from syntropiq.optimize.schema import LambdaVector


def test_adaptive_lambda_bounded_and_normalized():
    base = LambdaVector(0.25, 0.25, 0.25, 0.25).enforce_bounds(max_trust=None).normalize()
    new_lam, deltas = compute_adaptive_lambda(
        base=base,
        signals={
            "avg_trust": 0.55,
            "suppression_active": True,
            "drift_delta": 0.15,
            "r_score_latest": 0.95,
            "A_score": 45.0,
            "failure_rate": 0.3,
        },
        bounds={"max_step": 0.02, "max_trust": 0.3},
    )

    assert abs(sum(new_lam.as_dict().values()) - 1.0) < 1e-9
    assert all(0.0 <= v <= 1.0 for v in new_lam.as_dict().values())
    assert new_lam.l_trust <= 0.3 + 1e-9
    assert all(abs(v) <= 0.02 + 1e-12 for v in deltas.values())


def test_adaptive_lambda_is_deterministic_for_same_signals():
    base = LambdaVector(0.25, 0.25, 0.25, 0.25).enforce_bounds(max_trust=None).normalize()
    signals = {
        "avg_trust": 0.9,
        "suppression_active": False,
        "drift_delta": 0.05,
        "r_score_latest": 1.0,
        "A_score": 80.0,
        "failure_rate": 0.0,
        "bayes_risk_multiplier": 1.05,
    }
    a, d1 = compute_adaptive_lambda(base, signals, bounds={"max_step": 0.02, "max_trust": 0.3})
    b, d2 = compute_adaptive_lambda(base, signals, bounds={"max_step": 0.02, "max_trust": 0.3})

    assert a.as_dict() == pytest.approx(b.as_dict())
    assert d1 == pytest.approx(d2)
