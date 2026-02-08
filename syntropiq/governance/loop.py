"""
Governance Loop - Core Orchestration Engine

Orchestrates the complete governance cycle:
1. Task prioritization (Optimus)
2. Agent assignment (Syngentik Trust Engine)
3. Task execution
4. Trust score updates (Asymmetric Learning)
5. Reflection (RIF)
6. State persistence
"""

from typing import List, Dict, Any, Optional
from syntropiq.core.models import Task, Agent, ExecutionResult
from syntropiq.core.exceptions import CircuitBreakerTriggered, NoAgentsAvailable
from syntropiq.governance.prioritizer import OptimusPrioritizer
from syntropiq.governance.trust_engine import SyngentikTrustEngine
from syntropiq.governance.learning_engine import update_trust_scores
from syntropiq.governance.reflection_engine import evaluate_reflection
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
        trust_threshold: float = 0.7
    ):
        """
        Initialize governance loop.
        
        Args:
            state_manager: Persistent state manager for database operations
            trust_threshold: Minimum trust score for agent assignment
        """
        self.state = state_manager
        self.prioritizer = OptimusPrioritizer()
        self.trust_engine = SyngentikTrustEngine(trust_threshold=trust_threshold)
        
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
        2. Assign agents (Syngentik Trust Engine with Circuit-breaker, Suppression, Drift)
        3. Execute tasks
        4. Update trust scores (Asymmetric Learning)
        5. Generate reflection (RIF)
        6. Persist state to database
        
        Args:
            tasks: List of tasks to execute
            agents: Dictionary of available agents {agent_id: Agent}
            executor: Executor instance with execute() method
            run_id: Unique identifier for this cycle
            
        Returns:
            Dictionary with results, trust_updates, and reflection
            
        Raises:
            CircuitBreakerTriggered: When no agents meet trust threshold
            NoAgentsAvailable: When agent registry is empty
        """
        if not agents:
            raise NoAgentsAvailable("No agents available in registry")
        
        # Step 1: Prioritize tasks
        print(f"\n{'='*60}")
        print(f"🔄 Governance Cycle: {run_id}")
        print(f"{'='*60}")
        print(f"\n📋 Step 1: Prioritizing {len(tasks)} tasks...")
        prioritized = self.prioritizer.optimize(tasks)
        sorted_tasks = prioritized["sorted_tasks"]
        print(f"✅ Tasks prioritized: {[t.id for t in sorted_tasks[:3]]}..." if len(sorted_tasks) > 3 else f"✅ Tasks prioritized: {[t.id for t in sorted_tasks]}")
        
        # Step 2: Assign agents
        print(f"\n🎯 Step 2: Assigning agents (Trust threshold: {self.trust_engine.trust_threshold})...")
        try:
            assignments = self.trust_engine.assign_agents(sorted_tasks, agents)
            print(f"✅ Assigned {len(assignments)} tasks to agents")
            for assignment in assignments[:3]:  # Show first 3
                agent_trust = agents[assignment.agent_id].trust_score
                print(f"   • Task {assignment.task_id} → Agent {assignment.agent_id} (trust: {agent_trust:.2f})")
        except RuntimeError as e:
            # Circuit breaker triggered
            raise CircuitBreakerTriggered(str(e))
        
        # Step 3: Execute tasks
        print(f"\n⚙️  Step 3: Executing {len(assignments)} tasks...")
        results = []
        for assignment in assignments:
            task = next(t for t in sorted_tasks if t.id == assignment.task_id)
            agent = agents[assignment.agent_id]
            result = executor.execute(task, agent)
            results.append(result)
            status = "✅" if result.success else "❌"
            print(f"   {status} Task {result.task_id} by {result.agent_id} (latency: {result.latency:.3f}s)")
        
        # Step 4: Update trust scores
        print(f"\n📊 Step 4: Updating trust scores (η=0.02, γ=0.05)...")
        trust_updates = update_trust_scores(results, agents)
        for agent_id, new_score in trust_updates.items():
            old_score = agents[agent_id].trust_score
            delta = new_score - old_score
            arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
            print(f"   {arrow} {agent_id}: {old_score:.3f} → {new_score:.3f} (Δ {delta:+.3f})")
            # Update agent object
            agents[agent_id].trust_score = new_score
        
        # Step 5: Generate reflection
        print(f"\n🔍 Step 5: Generating reflection (RIF)...")
        reflection = evaluate_reflection(
            execution_results=results,
            trust_updates=trust_updates,
            prior_memory=None,  # TODO: Implement collective memory
            run_id=run_id
        )
        print(f"✅ Reflection generated (constraint_score: {reflection['constraint_score']}/4)")
        
        # Step 6: Persist state
        print(f"\n💾 Step 6: Persisting state to database...")
        self.state.update_trust_scores(trust_updates, reason=run_id)
        self.state.record_execution_results(results)
        self.state.record_reflection(reflection['reflection'], reflection)
        
        # Update suppression state in database
        for agent_id in self.trust_engine.suppressed_agents:
            cycles = self.trust_engine.suppressed_agents[agent_id]
            self.state.update_suppression_state(agent_id, is_suppressed=True, redemption_cycle=cycles)
        
        print(f"✅ State persisted")
        
        # Return cycle results
        print(f"\n{'='*60}")
        print(f"✅ Governance Cycle Complete")
        print(f"{'='*60}\n")
        
        return {
            "run_id": run_id,
            "results": results,
            "trust_updates": trust_updates,
            "reflection": reflection,
            "statistics": {
                "tasks_executed": len(results),
                "successes": sum(1 for r in results if r.success),
                "failures": sum(1 for r in results if not r.success),
                "avg_latency": sum(r.latency for r in results) / len(results) if results else 0,
            }
        }
    
    def get_agent_status(self, agent_id: str) -> Dict:
        """Get detailed status of an agent."""
        engine_status = self.trust_engine.get_agent_status(agent_id)
        db_history = self.state.get_trust_history(agent_id, limit=10)
        
        return {
            **engine_status,
            "trust_history_db": db_history
        }
    
    def get_system_statistics(self) -> Dict:
        """Get overall system statistics."""
        return self.state.get_statistics()