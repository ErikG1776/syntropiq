import pytest

from syntropiq.core.models import ExecutionResult
from syntropiq.governance.mutation_engine import MutationEngine


def _results(success: bool, n: int = 1) -> list[ExecutionResult]:
    return [
        ExecutionResult(
            task_id=f"task_{i}",
            agent_id="agent_a",
            success=success,
            latency=0.01,
            metadata={},
        )
        for i in range(n)
    ]


def test_warmup_blocks_loosening_on_high_success():
    engine = MutationEngine(
        initial_trust_threshold=0.70,
        initial_suppression_threshold=0.75,
        initial_drift_delta=0.10,
        mutation_rate=0.05,
        warmup_cycles=5,
        max_step=0.02,
    )

    out = engine.evaluate_and_mutate(_results(True), cycle_id="RUN:1", suppression_active=False)

    assert out["trust_threshold"] == 0.70
    assert out["suppression_threshold"] == 0.75
    assert out["drift_delta"] == 0.10


def test_post_warmup_loosens_with_max_step_cap():
    engine = MutationEngine(
        initial_trust_threshold=0.70,
        initial_suppression_threshold=0.75,
        initial_drift_delta=0.10,
        mutation_rate=0.05,
        warmup_cycles=1,
        max_step=0.02,
    )

    # warmup cycle: no loosening
    engine.evaluate_and_mutate(_results(True), cycle_id="RUN:1", suppression_active=False)
    out = engine.evaluate_and_mutate(_results(True), cycle_id="RUN:2", suppression_active=False)

    assert out["trust_threshold"] == pytest.approx(0.68)
    assert out["suppression_threshold"] == pytest.approx(0.73)
    assert out["drift_delta"] == pytest.approx(0.08)


def test_suppression_active_blocks_loosening():
    engine = MutationEngine(
        initial_trust_threshold=0.70,
        initial_suppression_threshold=0.75,
        initial_drift_delta=0.10,
        mutation_rate=0.05,
        warmup_cycles=0,
        max_step=0.02,
        suppression_dampen=True,
    )

    out = engine.evaluate_and_mutate(_results(True), cycle_id="RUN:1", suppression_active=True)

    assert out["trust_threshold"] == 0.70
    assert out["suppression_threshold"] == 0.75
    assert out["drift_delta"] == 0.10


def test_safety_band_invariant_always_holds():
    engine = MutationEngine(
        initial_trust_threshold=0.70,
        initial_suppression_threshold=0.75,
        initial_drift_delta=0.10,
        mutation_rate=0.05,
        warmup_cycles=0,
        max_step=0.02,
    )

    for i in range(1, 40):
        success = i % 2 == 0
        out = engine.evaluate_and_mutate(_results(success), cycle_id=f"RUN:{i}", suppression_active=False)

        assert 0.50 <= out["trust_threshold"] <= 0.95
        assert 0.60 <= out["suppression_threshold"] <= 0.95
        assert 0.05 <= out["drift_delta"] <= 0.20
        assert out["suppression_threshold"] >= out["trust_threshold"] + 0.05
