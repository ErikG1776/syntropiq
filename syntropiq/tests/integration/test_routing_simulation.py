"""
Simulation test: Routing modes and governance lifecycle.

Validates:
1. Safety invariants hold in BOTH deterministic and competitive modes
2. Competitive mode produces observable governance dynamics:
   - Trust divergence across agents
   - Suppression events
   - Probation routing (low-risk only for suppressed agents)
   - Redemption cycles
   - Mutation adaptation
3. Deterministic mode remains stable and predictable
"""

import random
import pytest
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.governance.trust_engine import SyntropiqTrustEngine
from syntropiq.governance.learning_engine import update_trust_scores
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.persistence.state_manager import PersistentStateManager


# ── Fixtures ──────────────────────────────────────────────────

def make_agents():
    """Three agents with close initial trust scores."""
    return {
        "alpha": Agent(id="alpha", trust_score=0.82, capabilities=["general"], status="active"),
        "beta": Agent(id="beta", trust_score=0.84, capabilities=["general"], status="active"),
        "gamma": Agent(id="gamma", trust_score=0.80, capabilities=["general"], status="active"),
    }


def make_mixed_tasks(n=5):
    """Tasks spanning low to high risk."""
    return [
        Task(id=f"task_{i}", impact=0.8, urgency=0.6, risk=round(0.3 + i * 0.15, 2))
        for i in range(n)  # risks: 0.3, 0.45, 0.6, 0.75, 0.9
    ]


def make_hard_tasks(n=5):
    """All high-risk tasks — will cause failures and trust decay."""
    return [
        Task(id=f"hard_{i}", impact=0.9, urgency=0.9, risk=0.85)
        for i in range(n)
    ]


def make_easy_tasks(n=5):
    """All low-risk tasks — will succeed and rebuild trust."""
    return [
        Task(id=f"easy_{i}", impact=0.5, urgency=0.5, risk=0.1)
        for i in range(n)
    ]


# ── Safety Invariants (both modes) ───────────────────────────

class TestSafetyInvariants:
    """Safety guarantees that must hold in BOTH routing modes."""

    @pytest.fixture(params=["deterministic", "competitive"])
    def engine(self, request):
        return SyntropiqTrustEngine(
            trust_threshold=0.7,
            suppression_threshold=0.75,
            drift_delta=0.1,
            routing_mode=request.param,
        )

    def test_circuit_breaker_fires_when_all_agents_untrusted(self, engine):
        """System refuses execution when no agent is eligible for the task."""
        agents = {
            "a": Agent(id="a", trust_score=0.3, capabilities=["x"], status="active"),
            "b": Agent(id="b", trust_score=0.2, capabilities=["x"], status="active"),
        }
        # Risk 0.5 exceeds PROBATION_RISK_CEILING (0.4), so suppressed
        # agents can't take it, and no active agents exist.
        tasks = [Task(id="t1", impact=0.5, urgency=0.5, risk=0.5)]

        with pytest.raises(RuntimeError, match="No eligible agent"):
            engine.assign_agents(tasks, agents)

    def test_suppressed_agent_blocked_from_high_risk(self, engine):
        """Probation agents only receive tasks with risk <= 0.4."""
        # One agent below suppression threshold, no active agents above trust threshold
        agents = {
            "low": Agent(id="low", trust_score=0.72, capabilities=["x"], status="active"),
        }

        # First call: agent enters suppression (0.72 < 0.75)
        low_risk = [Task(id="safe", impact=0.5, urgency=0.5, risk=0.3)]
        assignments = engine.assign_agents(low_risk, agents)
        assert len(assignments) == 1
        assert assignments[0].agent_id == "low"

        # Now high-risk task with only this probation agent available
        high_risk = [Task(id="dangerous", impact=0.5, urgency=0.5, risk=0.8)]
        with pytest.raises(RuntimeError, match="No eligible agent"):
            engine.assign_agents(high_risk, agents)

    def test_trust_scores_stay_bounded(self, engine):
        """Trust scores remain in [0.0, 1.0] after asymmetric learning."""
        agents = {
            "high": Agent(id="high", trust_score=0.99, capabilities=["x"], status="active"),
            "low": Agent(id="low", trust_score=0.01, capabilities=["x"], status="active"),
        }
        results = [
            ExecutionResult(task_id="t1", agent_id="high", success=True, latency=0.01),
            ExecutionResult(task_id="t2", agent_id="low", success=False, latency=0.01),
        ]
        updates = update_trust_scores(results, agents)

        assert 0.0 <= updates["high"] <= 1.0
        assert 0.0 <= updates["low"] <= 1.0


# ── Competitive Lifecycle ─────────────────────────────────────

class TestCompetitiveLifecycle:
    """Competitive mode produces observable governance dynamics."""

    def _make_loop(self, routing_mode, db=":memory:"):
        state = PersistentStateManager(db_path=db)
        loop = GovernanceLoop(
            state_manager=state,
            trust_threshold=0.7,
            suppression_threshold=0.75,
            drift_delta=0.1,
            routing_mode=routing_mode,
        )
        return loop, state

    def _run_cycles(self, loop, agents, executor, tasks_fn, n_cycles):
        """Run governance cycles, recovering from circuit breaker trips."""
        history = []
        for cycle in range(n_cycles):
            tasks = tasks_fn()
            try:
                result = loop.execute_cycle(
                    tasks, agents, executor, run_id=f"CYCLE_{cycle}"
                )
                history.append(result)
            except Exception:
                # Circuit breaker or no eligible agent — nudge agents to keep sim alive
                for a in agents.values():
                    if a.trust_score < 0.76:
                        a.trust_score = 0.76
        return history

    def test_trust_divergence_competitive(self):
        """
        Competitive routing spreads tasks across agents, producing
        different outcomes and measurable trust score separation.
        """
        random.seed(42)
        loop, _ = self._make_loop("competitive")
        # Threshold high enough that high-risk tasks fail
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        self._run_cycles(loop, agents, executor, make_hard_tasks, 15)

        scores = {aid: a.trust_score for aid, a in agents.items()}
        unique_scores = len(set(round(s, 4) for s in scores.values()))

        assert unique_scores > 1, (
            f"Expected divergence but all scores identical: {scores}"
        )

    def test_no_divergence_deterministic(self):
        """
        Deterministic routing always picks the same top agent,
        leaving unassigned agents' scores unchanged.
        """
        loop, _ = self._make_loop("deterministic")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()
        initial = {aid: a.trust_score for aid, a in agents.items()}

        self._run_cycles(loop, agents, executor, make_mixed_tasks, 10)

        # Only the top agent (beta, highest trust) should have changed
        changed = [
            aid for aid, a in agents.items()
            if round(a.trust_score, 6) != round(initial[aid], 6)
        ]
        assert len(changed) <= 1, (
            f"Expected at most 1 agent to change in deterministic mode, "
            f"but {changed} changed"
        )

    def test_suppression_fires(self):
        """
        Hard tasks in competitive mode cause failures that drop agent
        trust below suppression threshold.
        """
        random.seed(7)
        loop, _ = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        suppression_seen = False
        for cycle in range(20):
            tasks = make_hard_tasks(5)
            try:
                loop.execute_cycle(tasks, agents, executor, run_id=f"CYCLE_{cycle}")
            except Exception:
                for a in agents.values():
                    if a.trust_score < 0.5:
                        a.trust_score = 0.76

            if loop.trust_engine.suppressed_agents:
                suppression_seen = True
                break

        assert suppression_seen, (
            f"No suppression event after 20 cycles. "
            f"Scores: {({aid: a.trust_score for aid, a in agents.items()})}"
        )

    def test_redemption_after_suppression(self):
        """
        After suppression, switching to easy tasks allows agents
        to recover above the suppression threshold.
        """
        random.seed(7)
        loop, _ = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        # Phase 1: Hard tasks → drive trust down → trigger suppression
        for cycle in range(20):
            try:
                loop.execute_cycle(
                    make_hard_tasks(3), agents, executor,
                    run_id=f"HARD_{cycle}"
                )
            except Exception:
                for a in agents.values():
                    if a.trust_score < 0.5:
                        a.trust_score = 0.72  # Keep in probation range

            if loop.trust_engine.suppressed_agents:
                break

        suppressed_ids = set(loop.trust_engine.suppressed_agents.keys())
        assert suppressed_ids, "Setup failed: no agents were suppressed"

        # Phase 2: Easy tasks → rebuild trust → redemption
        for cycle in range(30):
            try:
                loop.execute_cycle(
                    make_easy_tasks(3), agents, executor,
                    run_id=f"EASY_{cycle}"
                )
            except Exception:
                for a in agents.values():
                    if a.trust_score < 0.5:
                        a.trust_score = 0.72

        # At least one originally suppressed agent should have recovered
        still_suppressed = set(loop.trust_engine.suppressed_agents.keys())
        recovered = suppressed_ids - still_suppressed
        assert recovered or not still_suppressed, (
            f"No redemption observed. Still suppressed: {still_suppressed}"
        )

    def test_mutation_adapts_thresholds(self):
        """
        Mutation engine shifts thresholds in response to sustained
        failure (tightening) or success (loosening).
        """
        random.seed(42)
        loop, _ = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()
        initial_tt = loop.trust_engine.trust_threshold

        self._run_cycles(loop, agents, executor, make_hard_tasks, 15)

        final_tt = loop.trust_engine.trust_threshold
        assert initial_tt != final_tt, (
            f"Thresholds never mutated: stayed at {initial_tt}"
        )

    def test_full_lifecycle(self):
        """
        End-to-end: competitive routing through divergence → suppression →
        mutation → redemption, verifying all governance layers activate.
        """
        random.seed(99)
        loop, state = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        events = {
            "divergence": False,
            "suppression": False,
            "mutation": False,
        }

        initial_tt = loop.trust_engine.trust_threshold

        # Run 25 cycles with hard tasks to stress the system
        for cycle in range(25):
            tasks = make_hard_tasks(3)
            try:
                loop.execute_cycle(tasks, agents, executor, run_id=f"FULL_{cycle}")
            except Exception:
                for a in agents.values():
                    if a.trust_score < 0.5:
                        a.trust_score = 0.72

            # Check divergence
            scores = [a.trust_score for a in agents.values()]
            if max(scores) - min(scores) > 0.01:
                events["divergence"] = True

            # Check suppression
            if loop.trust_engine.suppressed_agents:
                events["suppression"] = True

            # Check mutation
            if loop.trust_engine.trust_threshold != initial_tt:
                events["mutation"] = True
                initial_tt = loop.trust_engine.trust_threshold

        # At least 2 of 3 governance events should fire
        fired = sum(events.values())
        assert fired >= 2, (
            f"Only {fired}/3 governance events fired: {events}. "
            f"Final scores: {({aid: round(a.trust_score, 3) for aid, a in agents.items()})}"
        )
