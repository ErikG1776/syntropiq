from __future__ import annotations

from typing import Dict, Iterable


def compute_beta_posterior(successes: int, failures: int, alpha0: float = 1.0, beta0: float = 1.0) -> Dict[str, float]:
    alpha = float(alpha0) + max(0, int(successes))
    beta = float(beta0) + max(0, int(failures))
    denom = alpha + beta

    mean = alpha / denom if denom > 0 else 0.5
    uncertainty = 1.0 / denom if denom > 0 else 1.0

    # Low mean and/or high uncertainty increases risk multiplier.
    risk_multiplier = 1.0
    if mean < 0.6:
        risk_multiplier += min(0.2, (0.6 - mean) * 0.5)
    if uncertainty > 0.1:
        risk_multiplier += min(0.1, uncertainty)

    return {
        "alpha": alpha,
        "beta": beta,
        "posterior_mean": mean,
        "posterior_uncertainty": uncertainty,
        "suggested_risk_multiplier": risk_multiplier,
    }


def posterior_from_cycles(cycles: Iterable[dict], alpha0: float = 1.0, beta0: float = 1.0) -> Dict[str, float]:
    successes = 0
    failures = 0
    for cycle in cycles:
        successes += int(cycle.get("successes", 0))
        failures += int(cycle.get("failures", 0))
    return compute_beta_posterior(successes=successes, failures=failures, alpha0=alpha0, beta0=beta0)
