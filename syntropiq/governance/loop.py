"""
Governance Loop - Core Orchestration Engine

Orchestrates the complete governance cycle:
1. Task prioritization (Optimus)
2. Agent assignment (Syntropiq Trust Engine)
3. Task execution
4. Trust score updates (Asymmetric Learning)
5. Threshold mutation (Claim 5)
6. Reflection (RIF)
7. State persistence
"""

from typing import List, Dict, Any, Optional
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.core.exceptions import CircuitBreakerTriggered, NoAgentsAvailable
from syntropiq.governance.prioritizer import OptimusPrioritizer
from syntropiq.governance.trust_engine import SyntropiqTrustEngine
from syntropiq.governance.learning_engine import update_trust_scores
from syntropiq.governance.reflection_engine import evaluate_reflection
from syntropiq.governance.mutation_engine import MutationEngine
from syntropiq.persistence.state_manager import PersistentStateManager


class GovernanceLoop:
    """
    Main governance orchestrator.

    Coordinates all governance components to execute tasks with
    trust-based agent selection and continuous learning.
    """

    def __init__(
        self,
        state_manager: PersistentStateManager,
        trust_threshold: float = 0.7,
        suppression_threshold: float = 0.75,
        drift_delta: float = 0.1,
        routing_mode: str = "deterministic"
    ):
        """
        Initialize governance loop.

        Args:
            state_manager: Persistent state manager for database operations
            trust_threshold: Minimum trust score for agent assignment
            suppression_threshold: Minimum trust triggering suppression
            drift_delta: Drift detection sensitivity
            routing_mode: "deterministic" (top-1) or "competitive" (trust-weighted)
        """
        self.state = state_manager
        self.prioritizer = OptimusPrioritizer()
        self.trust_engine = SyntropiqTrustEngine(
            trust_threshold=trust_threshold,
            suppression_threshold=suppression_threshold,
            drift_delta=drift_delta,
            state_manager=state_manager,
            routing_mode=routing_mode
        )
        self.mutation_engine = MutationEngine(
            initial_trust_threshold=trust_threshold,
            initial_suppression_threshold=suppression_threshold,
            initial_drift_delta=drift_delta,
            state_manager=state_manager
        )

    def execute_cycle(
        self,
        tasks: List[Task],
        agents: Dict[str, Agent],
        executor: Any,
        run_id: str = "CYCLE_1"
    ) -> Dict[str, Any]:
        """
        Execute a complete governance cycle.

        Steps:
        1. Prioritize tasks (Optimus)
        2. Assign agents (Trust-ranked with circuit breaker)
        3. Execute tasks
        4. Update trust scores (Asymmetric Learning)
        5. Mutate thresholds (Claim 5)
        6. Generate reflection (RIF)
        7. Persist state to database

        Args:
            tasks: List of task objects
            agents: Dictionary of available agent objects
            executor: Executor instance with execute() method
            run_id: Unique identifier for this cycle

        Returns:
            Governance results dictionary

        Raises:
            CircuitBreakerTriggered: When no agents meet trust threshold
            NoAgentsAvailable: When agent registry is empty
        """
        if not agents:
            raise NoAgentsAvailable("No agents available in registry")

        # Step 1: Prioritize tasks
        prioritized = self.prioritizer.optimize(tasks)
        sorted_tasks = prioritized["sorted_tasks"]

        # Step 2: Assign agents
        try:
            assignments = self.trust_engine.assign_agents(
                sorted_tasks, agents
            )
        except RuntimeError as e:
            # Circuit breaker triggered
            raise CircuitBreakerTriggered(str(e))

        # Step 3: Execute tasks
        results: List[ExecutionResult] = []
        for assignment in assignments:
            task = next(t for t in sorted_tasks if t.id == assignment.task_id)
            agent = agents[assignment.agent_id]
            result = executor.execute(task, agent)
            results.append(result)

        # Step 4: Update trust scores
        trust_updates = update_trust_scores(results, agents)
        for aid, new_score in trust_updates.items():
            agents[aid].trust_score = new_score

        # Step 5: Mutate thresholds (Claim 5)
        mutation_result = self.mutation_engine.evaluate_and_mutate(
            execution_results=results,
            cycle_id=run_id
        )
        self.trust_engine.trust_threshold = mutation_result["trust_threshold"]
        self.trust_engine.suppression_threshold = mutation_result["suppression_threshold"]
        self.trust_engine.drift_delta = mutation_result["drift_delta"]

        # Step 6: Generate reflection
        reflection = evaluate_reflection(
            execution_results=results,
            trust_updates=trust_updates,
            prior_memory=None,
            run_id=run_id
        )

        # Step 7: Persist state
        self.state.update_trust_scores(trust_updates, reason=run_id)
        self.state.record_execution_results(results)
        self.state.record_reflection(reflection["reflection"], reflection)

        for aid in self.trust_engine.suppressed_agents:
            cycles = self.trust_engine.suppressed_agents[aid]
            self.state.update_suppression_state(aid, is_suppressed=True, redemption_cycle=cycles)

        return {
            "run_id": run_id,
            "results": results,
            "trust_updates": trust_updates,
            "reflection": reflection,
            "mutation": mutation_result,
            "statistics": {
                "tasks_executed": len(results),
                "successes": sum(1 for r in results if r.success),
                "failures": sum(1 for r in results if not r.success),
                "avg_latency": sum(r.latency for r in results) / len(results) if results else 0,
            }
        }

    def get_agent_status(self, agent_id: str) -> Dict:
        """Get detailed status of a specific agent."""
        engine_status = self.trust_engine.get_agent_status(agent_id)
        db_history = self.state.get_trust_history(agent_id, limit=10)
        return {**engine_status, "trust_history_db": db_history}

    def get_system_statistics(self) -> Dict:
        """Get overall system statistics."""
        return self.state.get_statistics()
