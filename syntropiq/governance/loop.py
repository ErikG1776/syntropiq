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

from datetime import datetime, timezone
from typing import Any, Dict, List

from syntropiq.core.exceptions import CircuitBreakerTriggered, NoAgentsAvailable
from syntropiq.core.models import Agent, ExecutionResult, Task
from syntropiq.governance.learning_engine import update_trust_scores
from syntropiq.governance.mutation_engine import MutationEngine
from syntropiq.governance.prioritizer import OptimusPrioritizer
from syntropiq.governance.reflection_engine import evaluate_reflection
from syntropiq.governance.trust_engine import SyntropiqTrustEngine
from syntropiq.optimize.config import get_default_lambda_vector, get_optimize_mode
from syntropiq.optimize.lambda_optimizer import optimize_tasks
from syntropiq.optimize.schema import OptimizeInput
from syntropiq.reflect.config import get_reflect_consensus_mode, get_reflect_mode
from syntropiq.reflect.consensus import run_consensus_reflect
from syntropiq.reflect.engine import run_reflect
from syntropiq.persistence.state_manager import PersistentStateManager


class GovernanceLoop:
    """Main governance orchestrator."""

    def __init__(
        self,
        state_manager: PersistentStateManager,
        trust_threshold: float = 0.7,
        suppression_threshold: float = 0.75,
        drift_delta: float = 0.1,
        routing_mode: str = "deterministic",
        telemetry: Any = None,
    ):
        self.state = state_manager
        self.prioritizer = OptimusPrioritizer()
        self.trust_engine = SyntropiqTrustEngine(
            trust_threshold=trust_threshold,
            suppression_threshold=suppression_threshold,
            drift_delta=drift_delta,
            state_manager=state_manager,
            routing_mode=routing_mode,
        )
        self.mutation_engine = MutationEngine(
            initial_trust_threshold=trust_threshold,
            initial_suppression_threshold=suppression_threshold,
            initial_drift_delta=drift_delta,
            state_manager=state_manager,
        )
        self.telemetry = telemetry
        self._cycle_sequence = 0

    def execute_cycle(
        self,
        tasks: List[Task],
        agents: Dict[str, Agent],
        executor: Any,
        run_id: str = "CYCLE_1",
    ) -> Dict[str, Any]:
        if not agents:
            raise NoAgentsAvailable("No agents available in registry")

        self._cycle_sequence += 1
        cycle_id = f"{run_id}:{self._cycle_sequence}"
        timestamp = datetime.now(timezone.utc).isoformat()

        trust_before = {aid: float(agent.trust_score) for aid, agent in agents.items()}
        status_before = {aid: str(agent.status) for aid, agent in agents.items()}

        threshold_before = {
            "trust_threshold": float(self.trust_engine.trust_threshold),
            "suppression_threshold": float(self.trust_engine.suppression_threshold),
            "drift_delta": float(self.trust_engine.drift_delta),
        }

        prioritized = self.prioritizer.optimize(tasks)
        sorted_tasks = prioritized["sorted_tasks"]

        if get_optimize_mode() == "integrate" and sorted_tasks:
            try:
                trust_by_agent = {aid: float(agent.trust_score) for aid, agent in agents.items()}
                optimize_input = OptimizeInput(
                    tasks=sorted_tasks,
                    trust_by_agent=trust_by_agent,
                    context={
                        "source": "governance_loop",
                        "run_id": run_id,
                        "cycle_id": cycle_id,
                    },
                )
                decision = optimize_tasks(
                    input=optimize_input,
                    lambda_vector=get_default_lambda_vector(),
                    run_id=run_id,
                )
                by_id = {task.id: task for task in sorted_tasks}
                sorted_tasks = [by_id[task_id] for task_id in decision.chosen_task_ids if task_id in by_id]

                if self.telemetry is not None:
                    telemetry_state = getattr(self.telemetry, "_state_manager", None)
                    if telemetry_state is not None and hasattr(telemetry_state, "save_optimization_event"):
                        telemetry_state.save_optimization_event(decision.to_dict())
            except Exception:
                # Keep integrate mode non-invasive: optimization failures must not block execution.
                pass

        try:
            assignments = self.trust_engine.assign_agents(sorted_tasks, agents)
        except RuntimeError as e:
            raise CircuitBreakerTriggered(str(e))

        assignment_count_by_agent: Dict[str, int] = {aid: 0 for aid in agents.keys()}
        for assignment in assignments:
            assignment_count_by_agent[assignment.agent_id] = (
                assignment_count_by_agent.get(assignment.agent_id, 0) + 1
            )

        total_assignments = max(1, len(assignments))
        authority_before: Dict[str, float] = {
            aid: 1.0 / max(1, len(agents)) for aid in agents.keys()
        }
        authority_after: Dict[str, float] = {
            aid: assignment_count_by_agent.get(aid, 0) / total_assignments for aid in agents.keys()
        }

        results: List[ExecutionResult] = []
        for assignment in assignments:
            task = next(t for t in sorted_tasks if t.id == assignment.task_id)
            agent = agents[assignment.agent_id]
            result = executor.execute(task, agent)
            results.append(result)

        trust_updates = update_trust_scores(results, agents)
        for aid, new_score in trust_updates.items():
            agents[aid].trust_score = new_score

        trust_after = {aid: float(agent.trust_score) for aid, agent in agents.items()}
        status_after = {aid: str(agent.status) for aid, agent in agents.items()}

        mutation_result = self.mutation_engine.evaluate_and_mutate(
            execution_results=results,
            cycle_id=cycle_id,
            suppression_active=bool(self.trust_engine.suppressed_agents),
        )
        self.trust_engine.trust_threshold = mutation_result["trust_threshold"]
        self.trust_engine.suppression_threshold = mutation_result["suppression_threshold"]
        self.trust_engine.drift_delta = mutation_result["drift_delta"]

        reflection = evaluate_reflection(
            execution_results=results,
            trust_updates=trust_updates,
            prior_memory=None,
            run_id=run_id,
        )

        self.state.update_trust_scores(trust_updates, reason=run_id)
        self.state.record_execution_results(results)
        self.state.record_reflection(reflection["reflection"], reflection)

        for aid in self.trust_engine.suppressed_agents:
            cycles = self.trust_engine.suppressed_agents[aid]
            self.state.update_suppression_state(aid, is_suppressed=True, redemption_cycle=cycles)

        successes = sum(1 for r in results if r.success)
        failures = sum(1 for r in results if not r.success)

        events = self._build_governance_events(
            run_id=run_id,
            cycle_id=cycle_id,
            timestamp=timestamp,
            agents=agents,
            trust_before=trust_before,
            trust_after=trust_after,
            status_before=status_before,
            status_after=status_after,
            authority_before=authority_before,
            authority_after=authority_after,
            trust_updates=trust_updates,
            threshold_before=threshold_before,
            mutation_result=mutation_result,
            reflection=reflection,
        )

        if self.telemetry is not None:
            try:
                if hasattr(self.telemetry, "publish_events"):
                    self.telemetry.publish_events(events)
                if hasattr(self.telemetry, "record_cycle"):
                    authority_delta = {
                        aid: round(authority_after.get(aid, 0.0) - authority_before.get(aid, 0.0), 6)
                        for aid in agents.keys()
                    }
                    self.telemetry.record_cycle(
                        {
                            "run_id": run_id,
                            "cycle_id": cycle_id,
                            "timestamp": timestamp,
                            "total_agents": len(agents),
                            "successes": successes,
                            "failures": failures,
                            "trust_delta_total": round(
                                sum(
                                    trust_after.get(aid, 0.0) - trust_before.get(aid, 0.0)
                                    for aid in agents.keys()
                                ),
                                6,
                            ),
                            "authority_redistribution": authority_delta,
                            "events": events,
                        }
                    )
            except Exception as telemetry_err:  # pragma: no cover
                print(f"Telemetry emit failed: {telemetry_err}")

        if get_reflect_mode() == "integrate":
            try:
                telemetry_state = getattr(self.telemetry, "_state_manager", None) if self.telemetry is not None else None
                if telemetry_state is not None and hasattr(telemetry_state, "save_reflect_decision"):
                    recent_cycles = (
                        telemetry_state.load_cycles_by_run_id(run_id, limit=50)
                        if hasattr(telemetry_state, "load_cycles_by_run_id")
                        else []
                    )
                    recent_events = (
                        telemetry_state.load_events_by_run_id(run_id, limit=200)
                        if hasattr(telemetry_state, "load_events_by_run_id")
                        else []
                    )
                    replay_rows = (
                        telemetry_state.load_replay_validations(run_id, limit=1)
                        if hasattr(telemetry_state, "load_replay_validations")
                        else []
                    )
                    latest_replay = float(replay_rows[0].get("r_score", 0.0)) if replay_rows else None

                    reflect_decision = run_reflect(
                        run_id=run_id,
                        cycle_id=cycle_id,
                        timestamp=timestamp,
                        trust_by_agent=trust_after,
                        thresholds={
                            "trust_threshold": float(self.trust_engine.trust_threshold),
                            "suppression_threshold": float(self.trust_engine.suppression_threshold),
                            "drift_delta": float(self.trust_engine.drift_delta),
                        },
                        suppression_active=bool(self.trust_engine.suppressed_agents),
                        recent_cycles=recent_cycles,
                        recent_events=recent_events,
                        horizon_steps=5,
                        theta=0.10,
                        weights_decay=0.85,
                        mode="integrate",
                        latest_replay_score=latest_replay,
                    )
                    telemetry_state.save_reflect_decision(reflect_decision.to_dict())
                    if get_reflect_consensus_mode() == "integrate" and hasattr(telemetry_state, "save_consensus_insight"):
                        consensus = run_consensus_reflect(
                            run_id=run_id,
                            cycle_id=cycle_id,
                            timestamp=timestamp,
                            trust_by_agent=trust_after,
                            thresholds={
                                "trust_threshold": float(self.trust_engine.trust_threshold),
                                "suppression_threshold": float(self.trust_engine.suppression_threshold),
                                "drift_delta": float(self.trust_engine.drift_delta),
                            },
                            suppression_active=bool(self.trust_engine.suppressed_agents),
                            recent_cycles=recent_cycles,
                            recent_events=recent_events,
                            horizon_steps=5,
                            theta=0.10,
                            latest_replay_score=latest_replay,
                        )
                        telemetry_state.save_consensus_insight(
                            {
                                "run_id": run_id,
                                "cycle_id": cycle_id,
                                "timestamp": timestamp,
                                **consensus,
                                "metadata": {"source": "governance_loop_integrate"},
                            }
                        )
            except Exception:
                # Reflect integration is advisory; failures must not impact cycle execution.
                pass

        return {
            "run_id": run_id,
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "results": results,
            "trust_updates": trust_updates,
            "reflection": reflection,
            "mutation": mutation_result,
            "statistics": {
                "tasks_executed": len(results),
                "successes": successes,
                "failures": failures,
                "avg_latency": sum(r.latency for r in results) / len(results) if results else 0,
            },
        }

    def _build_governance_events(
        self,
        run_id: str,
        cycle_id: str,
        timestamp: str,
        agents: Dict[str, Agent],
        trust_before: Dict[str, float],
        trust_after: Dict[str, float],
        status_before: Dict[str, str],
        status_after: Dict[str, str],
        authority_before: Dict[str, float],
        authority_after: Dict[str, float],
        trust_updates: Dict[str, float],
        threshold_before: Dict[str, float],
        mutation_result: Dict[str, float],
        reflection: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for aid in agents.keys():
            if aid not in trust_updates:
                continue
            events.append(
                {
                    "run_id": run_id,
                    "cycle_id": cycle_id,
                    "timestamp": timestamp,
                    "type": "trust_update",
                    "agent_id": aid,
                    "trust_before": round(trust_before.get(aid, 0.0), 6),
                    "trust_after": round(trust_after.get(aid, 0.0), 6),
                    "authority_before": round(authority_before.get(aid, 0.0), 6),
                    "authority_after": round(authority_after.get(aid, 0.0), 6),
                    "metadata": {
                        "delta": round(trust_after.get(aid, 0.0) - trust_before.get(aid, 0.0), 6)
                    },
                }
            )

        for aid in agents.keys():
            prev_status = status_before.get(aid, "unknown")
            next_status = status_after.get(aid, "unknown")
            if prev_status != next_status:
                event_type = "suppression" if next_status == "suppressed" else "status_change"
                events.append(
                    {
                        "run_id": run_id,
                        "cycle_id": cycle_id,
                        "timestamp": timestamp,
                        "type": event_type,
                        "agent_id": aid,
                        "trust_before": round(trust_before.get(aid, 0.0), 6),
                        "trust_after": round(trust_after.get(aid, 0.0), 6),
                        "authority_before": round(authority_before.get(aid, 0.0), 6),
                        "authority_after": round(authority_after.get(aid, 0.0), 6),
                        "metadata": {"status_before": prev_status, "status_after": next_status},
                    }
                )

        mutation_changed = any(
            abs(mutation_result.get(key, 0.0) - threshold_before.get(key, 0.0)) > 1e-12
            for key in ("trust_threshold", "suppression_threshold", "drift_delta")
        )
        if mutation_changed:
            avg_trust_before = sum(trust_before.values()) / max(1, len(trust_before))
            avg_trust_after = sum(trust_after.values()) / max(1, len(trust_after))
            events.append(
                {
                    "run_id": run_id,
                    "cycle_id": cycle_id,
                    "timestamp": timestamp,
                    "type": "mutation",
                    "agent_id": None,
                    "trust_before": round(avg_trust_before, 6),
                    "trust_after": round(avg_trust_after, 6),
                    "authority_before": 1.0,
                    "authority_after": 1.0,
                    "metadata": {
                        "trust_threshold_before": threshold_before.get("trust_threshold"),
                        "trust_threshold_after": mutation_result.get("trust_threshold"),
                        "suppression_threshold_before": threshold_before.get("suppression_threshold"),
                        "suppression_threshold_after": mutation_result.get("suppression_threshold"),
                        "drift_delta_before": threshold_before.get("drift_delta"),
                        "drift_delta_after": mutation_result.get("drift_delta"),
                    },
                }
            )

        events.append(
            {
                "run_id": run_id,
                "cycle_id": cycle_id,
                "timestamp": timestamp,
                "type": "reflection",
                "agent_id": None,
                "trust_before": 0.0,
                "trust_after": 0.0,
                "authority_before": 0.0,
                "authority_after": 0.0,
                "metadata": {
                    "constraint_score": reflection.get("constraint_score"),
                    "grounded": reflection.get("grounded"),
                    "recursive": reflection.get("recursive"),
                    "performative_flag": reflection.get("performative_flag"),
                    "contradiction": reflection.get("contradiction"),
                },
            }
        )

        return events

    def get_agent_status(self, agent_id: str) -> Dict:
        engine_status = self.trust_engine.get_agent_status(agent_id)
        db_history = self.state.get_trust_history(agent_id, limit=10)
        return {**engine_status, "trust_history_db": db_history}

    def get_system_statistics(self) -> Dict:
        return self.state.get_statistics()
