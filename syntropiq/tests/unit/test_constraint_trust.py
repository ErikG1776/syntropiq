"""
Unit tests for constraint_kernel.py and trust_engine.py.

Validates all constraint-checking logic for correctness and completeness.
"""
from __future__ import annotations

import pytest

from syntropiq.reflect.constraint_kernel import (
    _clamp,
    _normalized_violation,
    compute_constraint_penalties,
    default_constraints,
)
from syntropiq.reflect.schema import ConstraintSpec
from syntropiq.core.models import Task, Agent
from syntropiq.governance.trust_engine import SyntropiqTrustEngine


# ---------------------------------------------------------------------------
# _clamp
# ---------------------------------------------------------------------------

class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_low(self):
        assert _clamp(-1.0, 0.0, 1.0) == 0.0

    def test_above_high(self):
        assert _clamp(2.0, 0.0, 1.0) == 1.0

    def test_on_boundary(self):
        assert _clamp(0.0, 0.0, 1.0) == 0.0
        assert _clamp(1.0, 0.0, 1.0) == 1.0


# ---------------------------------------------------------------------------
# _normalized_violation
# ---------------------------------------------------------------------------

class TestNormalizedViolation:
    def test_max_no_violation(self):
        # value <= threshold → no violation
        assert _normalized_violation(0.10, 0.20, "max") == 0.0

    def test_max_violation(self):
        # value > threshold → positive violation
        v = _normalized_violation(0.30, 0.20, "max")
        assert v > 0.0
        assert v <= 1.0

    def test_max_violation_saturates(self):
        # Very large overshoot → clamped to 1.0
        assert _normalized_violation(1000.0, 0.10, "max") == 1.0

    def test_min_no_violation(self):
        # value >= threshold → no violation
        assert _normalized_violation(0.80, 0.70, "min") == 0.0

    def test_min_violation(self):
        # value < threshold → positive violation
        v = _normalized_violation(0.50, 0.70, "min")
        assert v > 0.0
        assert v <= 1.0

    def test_zero_threshold_no_div_zero(self):
        # threshold=0 uses 1e-9 guard
        v = _normalized_violation(1.0, 0.0, "max")
        assert v == 1.0  # clamped

    def test_exactly_at_threshold_max(self):
        assert _normalized_violation(0.20, 0.20, "max") == 0.0

    def test_exactly_at_threshold_min(self):
        assert _normalized_violation(0.70, 0.70, "min") == 0.0


# ---------------------------------------------------------------------------
# default_constraints
# ---------------------------------------------------------------------------

class TestDefaultConstraints:
    def test_returns_five_specs(self):
        specs = default_constraints()
        assert len(specs) == 5

    def test_weights_sum_to_one(self):
        specs = default_constraints()
        total = sum(s.weight for s in specs)
        assert total == pytest.approx(1.0)

    def test_suppression_rate_default_threshold_zero(self):
        # Any suppression (value=1) should produce a penalty
        specs = default_constraints()
        sr = next(s for s in specs if s.name == "suppression_rate")
        assert sr.threshold == 0.0

    def test_drift_max_custom(self):
        specs = default_constraints(drift_max=0.10)
        dl = next(s for s in specs if s.name == "drift_limit")
        assert dl.threshold == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# compute_constraint_penalties
# ---------------------------------------------------------------------------

class TestComputeConstraintPenalties:
    def _healthy_call(self, **overrides):
        kwargs = dict(
            trust_by_agent={"a": 0.90, "b": 0.85},
            thresholds={"trust_threshold": 0.70, "drift_delta": 0.10},
            suppression_count=0,
            instability=0.0,
            latest_replay_score=1.0,
            observed_drift=0.0,
        )
        kwargs.update(overrides)
        return compute_constraint_penalties(**kwargs)

    def test_returns_five_penalties(self):
        penalties, _ = self._healthy_call()
        assert len(penalties) == 5

    def test_total_penalty_bounded(self):
        penalties, total = self._healthy_call()
        assert 0.0 <= total <= 1.0

    def test_individual_penalties_bounded(self):
        penalties, _ = self._healthy_call()
        for p in penalties:
            assert 0.0 <= p.penalty <= 1.0, f"{p.name} penalty out of bounds: {p.penalty}"

    def test_no_penalty_healthy_system(self):
        # All agents trusted, no suppression, no drift, perfect replay
        penalties, total = self._healthy_call()
        assert total == pytest.approx(0.0)

    def test_trust_floor_penalty_fires(self):
        # min trust below trust_threshold triggers trust_floor penalty
        penalties, total = self._healthy_call(
            trust_by_agent={"a": 0.50, "b": 0.55},
            thresholds={"trust_threshold": 0.70, "drift_delta": 0.10},
        )
        trust_penalty = next(p for p in penalties if p.name == "trust_floor")
        assert trust_penalty.penalty > 0.0
        assert total > 0.0

    def test_suppression_rate_penalty_fires(self):
        # suppression_count=1, threshold=0 → full violation
        penalties, total = self._healthy_call(suppression_count=1)
        sr = next(p for p in penalties if p.name == "suppression_rate")
        assert sr.penalty > 0.0

    def test_suppression_rate_no_penalty_when_zero(self):
        penalties, _ = self._healthy_call(suppression_count=0)
        sr = next(p for p in penalties if p.name == "suppression_rate")
        assert sr.penalty == 0.0

    def test_drift_limit_penalty_fires_with_observed_drift(self):
        # observed_drift=0.25 > default drift_max threshold 0.20
        penalties, total = self._healthy_call(observed_drift=0.25)
        dl = next(p for p in penalties if p.name == "drift_limit")
        assert dl.penalty > 0.0

    def test_drift_limit_no_penalty_below_threshold(self):
        penalties, _ = self._healthy_call(observed_drift=0.05)
        dl = next(p for p in penalties if p.name == "drift_limit")
        assert dl.penalty == 0.0

    def test_drift_limit_uses_observed_not_config_param(self):
        # Config drift_delta=0.05 (very sensitive), but observed_drift=0 → no penalty
        penalties, _ = self._healthy_call(
            thresholds={"trust_threshold": 0.70, "drift_delta": 0.05},
            observed_drift=0.0,
        )
        dl = next(p for p in penalties if p.name == "drift_limit")
        assert dl.penalty == 0.0

    def test_instability_penalty_fires(self):
        # instability=0.10 > threshold 0.02
        penalties, _ = self._healthy_call(instability=0.10)
        inst = next(p for p in penalties if p.name == "instability")
        assert inst.penalty > 0.0

    def test_reproducibility_skipped_when_none(self):
        penalties, _ = self._healthy_call(latest_replay_score=None)
        rep = next(p for p in penalties if p.name == "reproducibility")
        assert rep.penalty == 0.0

    def test_reproducibility_penalty_fires_on_low_score(self):
        penalties, _ = self._healthy_call(latest_replay_score=0.80)
        rep = next(p for p in penalties if p.name == "reproducibility")
        assert rep.penalty > 0.0

    def test_empty_trust_dict_uses_zero_min_trust(self):
        # Should not crash; trust_floor value=0.0 → penalized relative to trust_threshold
        penalties, total = self._healthy_call(trust_by_agent={})
        assert total >= 0.0

    def test_custom_specs_honored(self):
        specs = [
            ConstraintSpec(name="trust_floor", weight=1.0, threshold=0.80, direction="min", penalty_scale=1.0)
        ]
        penalties, total = compute_constraint_penalties(
            trust_by_agent={"a": 0.70},
            thresholds={"trust_threshold": 0.80},
            suppression_count=0,
            specs=specs,
        )
        assert len(penalties) == 1
        assert penalties[0].name == "trust_floor"
        assert penalties[0].penalty > 0.0

    def test_penalty_values_stored_correctly(self):
        penalties, _ = self._healthy_call(
            trust_by_agent={"a": 0.50},
            thresholds={"trust_threshold": 0.70, "drift_delta": 0.10},
        )
        tf = next(p for p in penalties if p.name == "trust_floor")
        assert tf.value == pytest.approx(0.50)
        assert tf.threshold == pytest.approx(0.70)
        assert tf.weight == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# SyntropiqTrustEngine — constructor validation
# ---------------------------------------------------------------------------

class TestTrustEngineValidation:
    def test_valid_defaults(self):
        engine = SyntropiqTrustEngine()
        assert engine.trust_threshold == 0.7

    def test_trust_threshold_zero_rejected(self):
        with pytest.raises(ValueError, match="trust_threshold"):
            SyntropiqTrustEngine(trust_threshold=0.0)

    def test_trust_threshold_above_one_rejected(self):
        with pytest.raises(ValueError, match="trust_threshold"):
            SyntropiqTrustEngine(trust_threshold=1.1)

    def test_drift_delta_zero_rejected(self):
        with pytest.raises(ValueError, match="drift_delta"):
            SyntropiqTrustEngine(drift_delta=0.0)

    def test_drift_delta_negative_rejected(self):
        with pytest.raises(ValueError, match="drift_delta"):
            SyntropiqTrustEngine(drift_delta=-0.1)

    def test_invalid_routing_mode_rejected(self):
        with pytest.raises(ValueError, match="routing_mode"):
            SyntropiqTrustEngine(routing_mode="round_robin")

    def test_suppression_threshold_below_trust_threshold_rejected(self):
        with pytest.raises(ValueError, match="suppression_threshold"):
            SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.60)

    def test_suppression_threshold_equal_to_trust_threshold_allowed(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        assert engine.suppression_threshold == 0.70

    def test_suppression_threshold_defaults_to_trust_threshold(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.80)
        assert engine.suppression_threshold == 0.80


# ---------------------------------------------------------------------------
# SyntropiqTrustEngine — assignment logic
# ---------------------------------------------------------------------------

def _make_agent(agent_id: str, trust: float, status: str = "active") -> Agent:
    return Agent(id=agent_id, trust_score=trust, status=status, capabilities=[])


def _make_task(task_id: str, risk: float = 0.3) -> Task:
    return Task(id=task_id, impact=0.7, urgency=0.6, risk=risk, metadata={})


class TestTrustEngineAssignment:
    def test_healthy_agent_assigned(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70)
        tasks = [_make_task("t1")]
        agents = {"a": _make_agent("a", 0.90)}
        assignments = engine.assign_agents(tasks, agents)
        assert len(assignments) == 1
        assert assignments[0].agent_id == "a"

    def test_low_trust_agent_suppressed(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        tasks = [_make_task("t1")]
        agents = {"a": _make_agent("a", 0.90), "b": _make_agent("b", 0.50)}
        engine.assign_agents(tasks, agents)
        assert "b" in engine.suppressed_agents

    def test_circuit_breaker_fires_when_no_agents(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        tasks = [_make_task("t1", risk=0.9)]  # high risk — probation can't handle it
        # Agent trust too low for active, and after suppression it won't handle high-risk
        agents = {"a": _make_agent("a", 0.50)}
        with pytest.raises(RuntimeError):
            # First call suppresses agent_a, second call with no eligible agents triggers circuit breaker
            engine.assign_agents(tasks, agents)
            engine.assign_agents(tasks, agents)

    def test_circuit_breaker_no_agents_at_all(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        with pytest.raises(RuntimeError, match="No trusted agents"):
            engine.assign_agents([_make_task("t1")], {})

    def test_drift_detection_sets_warning(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, drift_delta=0.05)
        agent = _make_agent("a", 0.90)
        agents = {"a": agent}
        engine.assign_agents([_make_task("t1")], agents)
        # Simulate trust drop larger than drift_delta
        agent.trust_score = 0.80
        engine.assign_agents([_make_task("t2")], agents)
        assert engine.drift_warnings.get("a") is True

    def test_drift_warning_cleared_on_recovery(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        agent = _make_agent("a", 0.65)  # below threshold → suppressed
        agents = {"a": agent}
        engine.assign_agents([_make_task("t1")], {"b": _make_agent("b", 0.90)})
        # Manually set drift warning as if it fired before suppression
        engine.drift_warnings["a"] = True
        engine.suppressed_agents["a"] = 1
        # Recovery: trust rises above suppression_threshold
        agent.trust_score = 0.85
        engine._update_trust_history({"a": agent})
        engine._filter_agents({"a": agent})
        assert not engine.drift_warnings.get("a", False)

    def test_competitive_mode_zero_trust_no_crash(self):
        engine = SyntropiqTrustEngine(
            trust_threshold=0.70,
            suppression_threshold=0.70,
            routing_mode="competitive",
        )
        # Probation agents with zero trust_score must not crash random.choices
        tasks = [_make_task("t1", risk=0.2), _make_task("t2", risk=0.15)]
        agents = {"a": _make_agent("a", 0.90), "b": _make_agent("b", 0.0)}
        # First cycle: b gets suppressed
        engine.assign_agents(tasks, agents)
        # Second cycle: b is on probation with trust_score=0
        try:
            engine.assign_agents(tasks, agents)
        except ValueError as exc:
            pytest.fail(f"random.choices crashed with zero-weight candidates: {exc}")

    def test_deterministic_mode_picks_highest_trust(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, routing_mode="deterministic")
        tasks = [_make_task("t1")]
        agents = {
            "a": _make_agent("a", 0.75),
            "b": _make_agent("b", 0.95),
            "c": _make_agent("c", 0.80),
        }
        assignments = engine.assign_agents(tasks, agents)
        assert assignments[0].agent_id == "b"

    def test_probation_only_gets_low_risk_tasks(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        # Suppress agent b first
        agents = {"a": _make_agent("a", 0.90), "b": _make_agent("b", 0.50)}
        low_risk_task = _make_task("low", risk=0.2)
        high_risk_task = _make_task("high", risk=0.8)
        engine.assign_agents([low_risk_task], agents)
        # b is now suppressed/probation; high risk task must go to a
        assignments = engine.assign_agents([high_risk_task], agents)
        assert assignments[0].agent_id == "a"

    def test_get_agent_status_returns_correct_fields(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70)
        engine.assign_agents([_make_task("t1")], {"a": _make_agent("a", 0.90)})
        status = engine.get_agent_status("a")
        assert "trust_history" in status
        assert "is_suppressed" in status
        assert "suppression_cycles" in status
        assert "is_drifting" in status

    def test_max_redemption_cycles_permanently_excludes(self):
        engine = SyntropiqTrustEngine(trust_threshold=0.70, suppression_threshold=0.70)
        # Manually place agent in suppressed state at max cycles
        engine.suppressed_agents["b"] = SyntropiqTrustEngine.MAX_REDEMPTION_CYCLES + 1
        agent_b = _make_agent("b", 0.50)
        agent_a = _make_agent("a", 0.90)
        active, probation = engine._filter_agents({"a": agent_a, "b": agent_b})
        assert not any(a.id == "b" for a in active)
        assert not any(a.id == "b" for a in probation)
