from pathlib import Path

import pytest

from syntropiq.core.models import Task
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager


TOTAL_CYCLES = 50


def _build_phased_risks() -> list[float]:
    """Deterministic 50-cycle phased risk profile: mixed / hard / recovery / mixed."""
    mixed_a = [0.20, 0.55, 0.35, 0.60, 0.30, 0.65, 0.25, 0.50, 0.40, 0.58, 0.32, 0.62]
    hard = [0.85] * 13
    recovery = [0.10, 0.15, 0.12, 0.18, 0.08, 0.14, 0.11, 0.16, 0.09, 0.13, 0.10, 0.15]
    mixed_b = [0.28, 0.57, 0.34, 0.63, 0.22, 0.54, 0.38, 0.59, 0.27, 0.56, 0.33, 0.61, 0.29]

    phased = mixed_a + hard + recovery + mixed_b
    assert len(phased) == TOTAL_CYCLES
    return phased


def test_governance_stress_50_cycle_validation(tmp_path: Path):
    db_path = tmp_path / "governance_stress.db"
    state = PersistentStateManager(db_path=str(db_path))

    try:
        registry = AgentRegistry(state)
        loop = GovernanceLoop(
            state_manager=state,
            trust_threshold=0.70,
            suppression_threshold=0.75,
            drift_delta=0.10,
        )
        executor = DeterministicExecutor(decision_threshold=0.0, fixed_latency=0.001)

        # Register exactly 3 agents.
        registry.register_agent("agent_alpha", ["risk"], initial_trust_score=0.90)
        registry.register_agent("agent_beta", ["risk"], initial_trust_score=0.82)
        # Starts below suppression threshold to deterministically trigger suppression.
        registry.register_agent("agent_gamma", ["risk"], initial_trust_score=0.70)

        suppression_fired = False
        redemption_fired = False
        risks = _build_phased_risks()
        previously_suppressed = set()

        for cycle_idx, risk in enumerate(risks, start=1):
            run_id = f"STRESS_{cycle_idx:03d}"
            tasks = [
                Task(
                    id=f"task_{cycle_idx:03d}",
                    impact=0.7,
                    urgency=0.6,
                    risk=risk,
                    metadata={"phase_cycle": cycle_idx},
                )
            ]

            agents = registry.get_agents_dict()

            try:
                result = loop.execute_cycle(
                    tasks=tasks,
                    agents=agents,
                    executor=executor,
                    run_id=run_id,
                )
            except Exception as exc:  # pragma: no cover - explicit crash guard
                pytest.fail(f"Governance crashed during cycle {cycle_idx}: {exc}")

            # Trust must remain within [0, 1] for all known agents.
            for agent in agents.values():
                assert 0.0 <= agent.trust_score <= 1.0, (
                    f"Agent {agent.id} trust out of bounds at cycle {cycle_idx}: {agent.trust_score}"
                )
            for aid, trust in result["trust_updates"].items():
                assert 0.0 <= trust <= 1.0, (
                    f"Trust update out of bounds for {aid} at cycle {cycle_idx}: {trust}"
                )

            # Mutation thresholds must stay bounded.
            mutation = result["mutation"]
            assert 0.50 <= mutation["trust_threshold"] <= 0.95
            assert 0.60 <= mutation["suppression_threshold"] <= 0.95
            assert 0.05 <= mutation["drift_delta"] <= 0.20
            assert mutation["suppression_threshold"] >= mutation["trust_threshold"] + 0.05

            current_suppressed = set(loop.trust_engine.suppressed_agents.keys())
            if current_suppressed:
                suppression_fired = True

            # Redemption is a transition from suppressed -> no longer suppressed.
            if previously_suppressed - current_suppressed:
                redemption_fired = True

            previously_suppressed = current_suppressed

        assert suppression_fired, "Expected suppression to fire at least once"
        assert redemption_fired, "Expected redemption to fire at least once"

    finally:
        state.close()
