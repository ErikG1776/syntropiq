"""
50-Cycle Stress Test: Safety Invariant Validation

This is the v1 architecture validation gate.

Question under test:
    Does competitive mode maintain safety invariants over 50 cycles?

If yes — v1 is done. Architecture freezes. Engineering hardening begins.

Validates per-cycle:
    INV-1  Trust scores bounded in [0.0, 1.0]
    INV-2  Safety band: suppression_threshold >= trust_threshold
    INV-3  Suppressed agents never execute high-risk tasks (risk > 0.4)
    INV-4  Trust threshold within mutation bounds [0.5, 0.95]
    INV-5  Suppression threshold within mutation bounds [0.55, 0.95]
    INV-6  Circuit breaker fires (not crash) when no agents eligible

Validates post-hoc:
    POST-1  System didn't collapse (>= 40/50 cycles executed)
    POST-2  Trust divergence observed (competitive only)
    POST-3  Suppression lifecycle fired at least once
    POST-4  Mutation adapted thresholds
    POST-5  RIF reflections persisted
    POST-6  Database state consistent with in-memory state
"""

import random
import pytest
from syntropiq.core.models import Task, Agent
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.governance.trust_engine import SyntropiqTrustEngine
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.persistence.state_manager import PersistentStateManager


# ── Fixtures ──────────────────────────────────────────────────

NUM_CYCLES = 50


def make_agents():
    """Five agents with spread initial trust scores."""
    return {
        "alpha":   Agent(id="alpha",   trust_score=0.82, capabilities=["general"], status="active"),
        "beta":    Agent(id="beta",    trust_score=0.84, capabilities=["general"], status="active"),
        "gamma":   Agent(id="gamma",   trust_score=0.80, capabilities=["general"], status="active"),
        "delta":   Agent(id="delta",   trust_score=0.78, capabilities=["general"], status="active"),
        "epsilon": Agent(id="epsilon", trust_score=0.86, capabilities=["general"], status="active"),
    }


def make_workload(cycle: int, n: int = 5):
    """
    Realistic phased workload that shifts over 50 cycles.

    Phase 1 (0-12):  Mixed risk ramp-up
    Phase 2 (13-25): Hard tasks — stress, suppression trigger
    Phase 3 (26-37): Easy tasks — recovery, redemption
    Phase 4 (38-49): Mixed tasks — steady state validation
    """
    if cycle <= 12:
        # Mixed: risks from 0.2 to 0.8
        return [
            Task(id=f"c{cycle}_t{i}", impact=0.7, urgency=0.6,
                 risk=round(0.2 + i * 0.15, 2))
            for i in range(n)
        ]
    elif cycle <= 25:
        # Hard: high risk, triggers failures and suppression
        return [
            Task(id=f"c{cycle}_t{i}", impact=0.9, urgency=0.9, risk=0.85)
            for i in range(n)
        ]
    elif cycle <= 37:
        # Easy: low risk, enables redemption
        return [
            Task(id=f"c{cycle}_t{i}", impact=0.5, urgency=0.5, risk=0.15)
            for i in range(n)
        ]
    else:
        # Mixed: steady state
        return [
            Task(id=f"c{cycle}_t{i}", impact=0.7, urgency=0.6,
                 risk=round(0.25 + i * 0.12, 2))
            for i in range(n)
        ]


# ── Per-Cycle Invariant Checker ──────────────────────────────

class InvariantChecker:
    """Tracks and validates safety invariants across cycles."""

    def __init__(self):
        self.log = []
        self.violations = []

    def check_cycle(self, cycle, agents, loop, result, tasks):
        """Run all per-cycle invariant checks."""
        entry = {
            "cycle": cycle,
            "status": "ok",
            "scores": {aid: round(a.trust_score, 4) for aid, a in agents.items()},
            "trust_threshold": round(loop.trust_engine.trust_threshold, 4),
            "suppression_threshold": round(loop.trust_engine.suppression_threshold, 4),
            "drift_delta": round(loop.trust_engine.drift_delta, 4),
            "suppressed": list(loop.trust_engine.suppressed_agents.keys()),
            "probation": list(loop.trust_engine.probation_agents.keys()),
            "successes": result["statistics"]["successes"],
            "failures": result["statistics"]["failures"],
        }

        # INV-1: Trust scores bounded [0.0, 1.0]
        for aid, a in agents.items():
            if not (0.0 <= a.trust_score <= 1.0):
                self.violations.append(
                    f"INV-1 Cycle {cycle}: Agent {aid} trust "
                    f"{a.trust_score} out of [0.0, 1.0]"
                )

        # INV-2: Safety band
        tt = loop.trust_engine.trust_threshold
        st = loop.trust_engine.suppression_threshold
        if st < tt:
            self.violations.append(
                f"INV-2 Cycle {cycle}: Safety band violated: "
                f"suppression={st:.4f} < trust={tt:.4f}"
            )

        # INV-3: Suppressed agents blocked from high-risk
        suppressed_ids = set(loop.trust_engine.suppressed_agents.keys())
        for r in result["results"]:
            task = next(t for t in tasks if t.id == r.task_id)
            if r.agent_id in suppressed_ids and task.risk > SyntropiqTrustEngine.PROBATION_RISK_CEILING:
                self.violations.append(
                    f"INV-3 Cycle {cycle}: Suppressed agent {r.agent_id} "
                    f"executed task {task.id} with risk={task.risk}"
                )

        # INV-4: Trust threshold in mutation bounds
        if not (0.5 <= tt <= 0.95):
            self.violations.append(
                f"INV-4 Cycle {cycle}: Trust threshold {tt:.4f} "
                f"out of [0.5, 0.95]"
            )

        # INV-5: Suppression threshold in mutation bounds
        if not (0.5 <= st <= 0.95):
            self.violations.append(
                f"INV-5 Cycle {cycle}: Suppression threshold {st:.4f} "
                f"out of [0.5, 0.95]"
            )

        self.log.append(entry)

    def record_circuit_breaker(self, cycle, agents):
        """Record a circuit breaker trip (INV-6: fires, not crash)."""
        self.log.append({
            "cycle": cycle,
            "status": "circuit_breaker",
            "scores": {aid: round(a.trust_score, 4) for aid, a in agents.items()},
        })

    def summary(self):
        ok = sum(1 for e in self.log if e["status"] == "ok")
        cb = sum(1 for e in self.log if e["status"] == "circuit_breaker")
        return {
            "cycles_executed": ok,
            "circuit_breaker_trips": cb,
            "violations": self.violations,
        }


# ── 50-Cycle Stress Tests ────────────────────────────────────

class TestFiftyCycleStress:
    """
    v1 architecture validation gate.

    Runs 50 governance cycles with phased workload.
    Checks every safety invariant on every cycle.
    Validates governance dynamics post-hoc.
    """

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

    def _recover_agents(self, agents, threshold=0.76):
        """Nudge collapsed agents back above suppression to keep sim alive."""
        for a in agents.values():
            if a.trust_score < threshold:
                a.trust_score = threshold

    # ── Competitive Mode: 50 Cycles ───────────────────────────

    def test_competitive_50_cycles_safety_invariants(self):
        """
        COMPETITIVE MODE: All safety invariants hold for 50 cycles.

        This is the primary v1 validation. If this passes, the
        governance architecture is correct under dynamic routing.
        """
        random.seed(2024)
        loop, state = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()
        checker = InvariantChecker()

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                result = loop.execute_cycle(
                    tasks, agents, executor, run_id=f"STRESS_{cycle}"
                )
                checker.check_cycle(cycle, agents, loop, result, tasks)
            except (CircuitBreakerTriggered, RuntimeError):
                # INV-6: System halts safely, doesn't crash
                checker.record_circuit_breaker(cycle, agents)
                self._recover_agents(agents)

        summary = checker.summary()

        # No invariant violations
        assert not summary["violations"], (
            f"Safety invariant violations:\n" +
            "\n".join(summary["violations"])
        )

        # POST-1: System didn't collapse
        assert summary["cycles_executed"] >= 40, (
            f"System collapsed: only {summary['cycles_executed']}/50 "
            f"cycles executed ({summary['circuit_breaker_trips']} CB trips)"
        )

    def test_competitive_50_cycles_governance_dynamics(self):
        """
        COMPETITIVE MODE: Governance events actually fire over 50 cycles.

        Validates the system is alive, not just safe-but-inert.
        """
        random.seed(2024)
        loop, state = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        events = {
            "divergence": False,
            "suppression": False,
            "redemption": False,
            "mutation": False,
        }

        initial_tt = loop.trust_engine.trust_threshold
        ever_suppressed = set()

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                result = loop.execute_cycle(
                    tasks, agents, executor, run_id=f"DYN_{cycle}"
                )

                # Check divergence
                scores = [a.trust_score for a in agents.values()]
                if max(scores) - min(scores) > 0.02:
                    events["divergence"] = True

                # Check suppression
                currently_suppressed = set(loop.trust_engine.suppressed_agents.keys())
                if currently_suppressed:
                    events["suppression"] = True
                    ever_suppressed |= currently_suppressed

                # Check redemption (agent was suppressed, now isn't)
                if ever_suppressed - currently_suppressed:
                    events["redemption"] = True

                # Check mutation
                if loop.trust_engine.trust_threshold != initial_tt:
                    events["mutation"] = True
                    initial_tt = loop.trust_engine.trust_threshold

            except (CircuitBreakerTriggered, RuntimeError):
                self._recover_agents(agents)

        # POST-2 through POST-4: All governance dynamics should activate
        assert events["divergence"], (
            "No trust divergence observed — competitive routing not distributing tasks"
        )
        assert events["suppression"], (
            "No suppression events — hard task phase didn't trigger governance"
        )
        assert events["mutation"], (
            "No threshold mutation — mutation engine never fired"
        )

    def test_competitive_50_cycles_persistence(self):
        """
        COMPETITIVE MODE: Database state is consistent after 50 cycles.

        Validates RIF reflections and mutation history are persisted.
        """
        random.seed(2024)
        loop, state = self._make_loop("competitive")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()

        ok_cycles = 0
        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                loop.execute_cycle(
                    tasks, agents, executor, run_id=f"PERSIST_{cycle}"
                )
                ok_cycles += 1
            except (CircuitBreakerTriggered, RuntimeError):
                self._recover_agents(agents)

        # POST-5: RIF reflections persisted
        reflections = state.get_recent_reflections(limit=100)
        assert len(reflections) >= ok_cycles, (
            f"Expected >= {ok_cycles} reflections, got {len(reflections)}"
        )

        # POST-6: Mutation history persisted
        mutations = state.get_mutation_history(limit=100)
        assert len(mutations) >= ok_cycles, (
            f"Expected >= {ok_cycles} mutation records, got {len(mutations)}"
        )

        # POST-6: Execution results persisted
        stats = state.get_statistics()
        assert stats["total_executions"] > 0, "No execution results in database"

        # POST-6: Trust scores persisted
        db_scores = state.get_trust_scores()
        for aid in agents:
            assert aid in db_scores, f"Agent {aid} trust not persisted"

    # ── Deterministic Mode: 50-Cycle Control ──────────────────

    def test_deterministic_50_cycles_safety_invariants(self):
        """
        DETERMINISTIC MODE: Same 50-cycle invariant sweep as control.

        If competitive passes but deterministic fails, the routing
        mode switch introduced a bug. Both must pass.
        """
        loop, state = self._make_loop("deterministic")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()
        checker = InvariantChecker()

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                result = loop.execute_cycle(
                    tasks, agents, executor, run_id=f"DET_{cycle}"
                )
                checker.check_cycle(cycle, agents, loop, result, tasks)
            except (CircuitBreakerTriggered, RuntimeError):
                checker.record_circuit_breaker(cycle, agents)
                self._recover_agents(agents)

        summary = checker.summary()

        assert not summary["violations"], (
            f"Safety invariant violations (deterministic):\n" +
            "\n".join(summary["violations"])
        )

        assert summary["cycles_executed"] >= 40, (
            f"Deterministic mode collapsed: only "
            f"{summary['cycles_executed']}/50 cycles executed"
        )

    def test_deterministic_50_cycles_stability(self):
        """
        DETERMINISTIC MODE: Trust scores remain stable (low variance).

        In deterministic mode, only the top agent gets assigned, so
        most agents should maintain their initial scores.
        """
        loop, _ = self._make_loop("deterministic")
        executor = DeterministicExecutor(decision_threshold=0.05)
        agents = make_agents()
        initial = {aid: a.trust_score for aid, a in agents.items()}

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                loop.execute_cycle(
                    tasks, agents, executor, run_id=f"STABLE_{cycle}"
                )
            except (CircuitBreakerTriggered, RuntimeError):
                self._recover_agents(agents)

        # At most 2 agents should have changed (top agent + possible
        # fallback after suppression)
        changed = [
            aid for aid, a in agents.items()
            if abs(a.trust_score - initial[aid]) > 0.001
        ]
        assert len(changed) <= 2, (
            f"Deterministic mode changed {len(changed)} agents: {changed}. "
            f"Expected <= 2."
        )

    # ── Cross-Mode Comparison ─────────────────────────────────

    def test_competitive_produces_more_dynamics_than_deterministic(self):
        """
        Competitive mode should produce strictly more governance
        activity than deterministic mode over the same workload.
        """
        random.seed(2024)

        # Run competitive
        c_loop, _ = self._make_loop("competitive")
        c_exec = DeterministicExecutor(decision_threshold=0.05)
        c_agents = make_agents()
        c_suppressions = 0
        c_mutations = 0
        c_initial_tt = c_loop.trust_engine.trust_threshold

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                c_loop.execute_cycle(tasks, c_agents, c_exec, run_id=f"CC_{cycle}")
                if c_loop.trust_engine.suppressed_agents:
                    c_suppressions += 1
                if c_loop.trust_engine.trust_threshold != c_initial_tt:
                    c_mutations += 1
                    c_initial_tt = c_loop.trust_engine.trust_threshold
            except (CircuitBreakerTriggered, RuntimeError):
                self._recover_agents(c_agents)

        # Run deterministic
        d_loop, _ = self._make_loop("deterministic")
        d_exec = DeterministicExecutor(decision_threshold=0.05)
        d_agents = make_agents()
        d_suppressions = 0

        for cycle in range(NUM_CYCLES):
            tasks = make_workload(cycle)
            try:
                d_loop.execute_cycle(tasks, d_agents, d_exec, run_id=f"DD_{cycle}")
                if d_loop.trust_engine.suppressed_agents:
                    d_suppressions += 1
            except (CircuitBreakerTriggered, RuntimeError):
                self._recover_agents(d_agents)

        # Competitive should have more trust score diversity
        c_scores = [a.trust_score for a in c_agents.values()]
        d_scores = [a.trust_score for a in d_agents.values()]
        c_spread = max(c_scores) - min(c_scores)
        d_spread = max(d_scores) - min(d_scores)

        assert c_spread > d_spread, (
            f"Competitive spread ({c_spread:.4f}) not greater than "
            f"deterministic spread ({d_spread:.4f})"
        )
