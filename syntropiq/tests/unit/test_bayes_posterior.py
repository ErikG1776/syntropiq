import pytest

from syntropiq.optimize.bayes_posterior import compute_beta_posterior, posterior_from_cycles


def test_beta_posterior_deterministic_values():
    out = compute_beta_posterior(successes=9, failures=3, alpha0=1, beta0=1)
    assert out["alpha"] == pytest.approx(10)
    assert out["beta"] == pytest.approx(4)
    assert out["posterior_mean"] == pytest.approx(10 / 14)
    assert out["posterior_uncertainty"] == pytest.approx(1 / 14)
    assert out["suggested_risk_multiplier"] >= 1.0


def test_posterior_from_cycles_counts_success_failure():
    cycles = [
        {"successes": 3, "failures": 1},
        {"successes": 1, "failures": 2},
    ]
    out = posterior_from_cycles(cycles)
    assert out["alpha"] == pytest.approx(1 + 4)
    assert out["beta"] == pytest.approx(1 + 3)
