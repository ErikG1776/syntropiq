"""
Syntropiq Trust Engine - Agent Assignment with Governance Features

Implements governance mechanisms:
- Circuit-breaker pattern
- Suppression with redemption cycles
- Preemptive drift-based decision making
"""

import random
from typing import List, Dict, Optional, TYPE_CHECKING
from syntropiq.core.models import Task, Agent, Assignment

if TYPE_CHECKING:
    from syntropiq.persistence.state_manager import PersistentStateManager


class SyntropiqTrustEngine:
    """
    Trust-based agent assignment engine with governance features.
    """

    MAX_REDEMPTION_CYCLES = 4
    PROBATION_RISK_CEILING = 0.4
    PROBATION_TASK_QUOTA = 2  # Low-risk tasks per cycle for redemption

    def __init__(
        self,
        trust_threshold: float = 0.7,
        suppression_threshold: Optional[float] = None,
        drift_delta: float = 0.1,
        state_manager: Optional["PersistentStateManager"] = None,
        routing_mode: str = "deterministic"
    ):
        """
        Args:
            trust_threshold: Minimum trust required for assignment
            suppression_threshold: Threshold for entering suppression.
                                   Defaults to trust_threshold.
            drift_delta: Performance drop threshold for drift detection.
            routing_mode: "deterministic" (top-1) or "competitive" (trust-weighted)
        """
        self.trust_threshold = trust_threshold
        self.suppression_threshold = (
            suppression_threshold if suppression_threshold is not None else trust_threshold
        )
        self.drift_delta = drift_delta
        self.state_manager = state_manager
        self.routing_mode = routing_mode

        self.trust_history: Dict[str, List[float]] = {}
        self.suppressed_agents: Dict[str, int] = {}
        self.probation_agents: Dict[str, int] = {}
        self.drift_warnings: Dict[str, bool] = {}

    # ---------------------------------------------------------
    # PUBLIC ENTRYPOINT
    # ---------------------------------------------------------

    def assign_agents(
        self,
        tasks: List[Task],
        agents: Dict[str, Agent]
    ) -> List[Assignment]:

        self._update_trust_history(agents)
        self._detect_drift()

        active_agents, probation_agents = self._filter_agents(agents)

        # Circuit breaker
        if not active_agents and not probation_agents:
            raise RuntimeError(
                "No trusted agents available — system halted to avoid unsafe execution."
            )

        return self._create_assignments(tasks, active_agents, probation_agents)

    # ---------------------------------------------------------
    # TRUST HISTORY + DRIFT
    # ---------------------------------------------------------

    def _update_trust_history(self, agents: Dict[str, Agent]) -> None:
        for agent_id, agent in agents.items():
            history = self.trust_history.setdefault(agent_id, [])
            history.append(agent.trust_score)
            if len(history) > 10:
                self.trust_history[agent_id] = history[-10:]

    def _detect_drift(self) -> None:
        for agent_id, history in self.trust_history.items():
            if len(history) >= 2:
                delta = history[-1] - history[-2]
                if delta < -self.drift_delta:
                    self.drift_warnings[agent_id] = True
                elif delta > 0:
                    self.drift_warnings[agent_id] = False

    # ---------------------------------------------------------
    # SUPPRESSION + REDEMPTION
    # ---------------------------------------------------------

    def _filter_agents(self, agents: Dict[str, Agent]):

        active_agents = []
        probation_agents = []

        for agent_id, agent in agents.items():

            if agent_id in self.suppressed_agents:
                cycles = self.suppressed_agents[agent_id]

                if agent.trust_score >= self.suppression_threshold:
                    # Recovered
                    del self.suppressed_agents[agent_id]
                    if agent_id in self.probation_agents:
                        del self.probation_agents[agent_id]
                    agent.status = "active"
                    if self.state_manager:
                        self.state_manager.update_agent_status(agent_id, "active")
                    active_agents.append(agent)
                elif cycles <= self.MAX_REDEMPTION_CYCLES:
                    self.suppressed_agents[agent_id] += 1
                    self.probation_agents[agent_id] = self.suppressed_agents[agent_id]
                    probation_agents.append(agent)
                else:
                    # Permanently excluded
                    if agent_id in self.probation_agents:
                        del self.probation_agents[agent_id]
                    continue

            else:
                if agent.trust_score < self.suppression_threshold:
                    self.suppressed_agents[agent_id] = 1
                    self.probation_agents[agent_id] = 1
                    agent.status = "suppressed"
                    if self.state_manager:
                        self.state_manager.update_agent_status(agent_id, "suppressed")
                    probation_agents.append(agent)
                elif agent.trust_score >= self.trust_threshold:
                    active_agents.append(agent)

        return active_agents, probation_agents

    # ---------------------------------------------------------
    # TRUST-RANKED ROUTING
    # ---------------------------------------------------------

    def _create_assignments(
        self,
        tasks: List[Task],
        active_agents: List[Agent],
        probation_agents: List[Agent]
    ) -> List[Assignment]:

        assignments = []

        # Rank active agents (healthy first, then drifting)
        healthy = sorted(
            [a for a in active_agents if not self.drift_warnings.get(a.id, False)],
            key=lambda a: a.trust_score,
            reverse=True
        )
        drifting = sorted(
            [a for a in active_agents if self.drift_warnings.get(a.id, False)],
            key=lambda a: a.trust_score,
            reverse=True
        )

        ranked_active = healthy + drifting
        ranked_probation = sorted(
            probation_agents,
            key=lambda a: a.trust_score,
            reverse=True
        )

        # Redemption requires work: reserve low-risk tasks for probation agents
        # so they can earn trust back. Without this, active agents consume
        # everything and suppressed agents can never recover.
        probation_assigned = 0

        for task in tasks:
            assigned = False

            # Route low-risk tasks to probation agents for redemption
            if (ranked_probation
                    and task.risk <= self.PROBATION_RISK_CEILING
                    and probation_assigned < self.PROBATION_TASK_QUOTA):
                agent = self._select_agent(ranked_probation)
                assignments.append(Assignment(task_id=task.id, agent_id=agent.id))
                probation_assigned += 1
                assigned = True

            # Active agents handle everything else
            elif ranked_active:
                agent = self._select_agent(ranked_active)
                assignments.append(Assignment(task_id=task.id, agent_id=agent.id))
                assigned = True

            # Last resort: probation for remaining low-risk
            elif ranked_probation and task.risk <= self.PROBATION_RISK_CEILING:
                agent = self._select_agent(ranked_probation)
                assignments.append(Assignment(task_id=task.id, agent_id=agent.id))
                assigned = True

            if not assigned:
                raise RuntimeError(
                    f"No eligible agent for task {task.id} (risk={task.risk})"
                )

        return assignments

    def _select_agent(self, candidates: List[Agent]) -> Agent:
        """
        Select an agent from candidates based on routing mode.

        deterministic: Always pick the highest-trust agent (top-1).
        competitive: Trust-weighted probabilistic selection.
            P(agent_i) = trust_i / sum(all trust scores)
            Higher trust still dominates, but all eligible agents execute.
        """
        if self.routing_mode == "competitive" and len(candidates) > 1:
            weights = [a.trust_score for a in candidates]
            return random.choices(candidates, weights=weights, k=1)[0]
        return candidates[0]

    # ---------------------------------------------------------
    # STATUS INTROSPECTION
    # ---------------------------------------------------------

    def get_agent_status(self, agent_id: str) -> Dict:
        return {
            "trust_history": self.trust_history.get(agent_id, []),
            "is_suppressed": agent_id in self.suppressed_agents,
            "suppression_cycles": self.suppressed_agents.get(agent_id, 0),
            "is_drifting": self.drift_warnings.get(agent_id, False)
        }
