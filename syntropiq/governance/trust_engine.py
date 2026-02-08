"""
Syngentik Trust Engine - Agent Assignment with Governance Features

Implements patented governance mechanisms:
- Circuit-breaker pattern (Claim 2)
- Suppression with redemption cycles (Claim 3)
- Preemptive drift-based decision making (Claim 4)
"""

from typing import List, Dict, Optional
from syntropiq.core.models import Task, Agent, Assignment


class SyngentikTrustEngine:
    """
    Trust-based agent assignment engine with advanced governance features.

    Patent Claims Implemented:
    - Claim 2: Circuit-breaker halts execution when all agents below threshold
    - Claim 3: Suppression with redemption cycles for underperforming agents
    - Claim 4: Preemptive drift detection and routing adjustments
    """

    # Patent parameters
    SUPPRESSION_THRESHOLD = 0.75  # T_supp: Agents below this are suppressed
    MAX_REDEMPTION_CYCLES = 4     # M: Window for agents to recover
    DRIFT_DETECTION_DELTA = 0.1   # Δ: Threshold for detecting performance drift

    def __init__(self, trust_threshold: float = 0.7):
        """
        Initialize trust engine.

        Args:
            trust_threshold: Minimum trust score for agent assignment (default: 0.7)
        """
        self.trust_threshold = trust_threshold
        self.trust_history: Dict[str, List[float]] = {}  # Agent trust score history
        self.suppressed_agents: Dict[str, int] = {}      # {agent_id: cycles_suppressed}
        self.drift_warnings: Dict[str, bool] = {}        # Agents showing drift

    def assign_agents(
        self,
        tasks: List[Task],
        agents: Dict[str, Agent],
        threshold: Optional[float] = None
    ) -> List[Assignment]:
        """
        Assign agents to tasks with governance constraints.

        Implements:
        1. Trust history tracking (for drift detection)
        2. Drift detection (preemptive decision making)
        3. Suppression/redemption cycle management
        4. Circuit-breaker pattern

        Args:
            tasks: List of tasks to assign
            agents: Dictionary of available agents {agent_id: Agent}
            threshold: Override default trust threshold

        Returns:
            List of task-agent assignments

        Raises:
            RuntimeError: Circuit-breaker triggered (no trusted agents available)
        """
        if threshold is None:
            threshold = self.trust_threshold

        # Step 1: Update trust history for all agents
        self._update_trust_history(agents)

        # Step 2: Detect drift (Claim 4: Preemptive drift detection)
        self._detect_drift()

        # Step 3: Filter agents based on trust and suppression status
        active_agents = self._filter_agents(agents, threshold)

        # Step 4: Circuit breaker (Claim 2)
        if not active_agents:
            print(f"🛑 Circuit Breaker Triggered: No agents above trust threshold ({threshold})")
            print(f"   Suppressed agents: {list(self.suppressed_agents.keys())}")
            print(f"   Drifting agents: {[k for k, v in self.drift_warnings.items() if v]}")
            raise RuntimeError("No trusted agents available — system halted to avoid unsafe execution.")

        # Step 5: Assign tasks to active agents
        assignments = self._create_assignments(tasks, active_agents)

        return assignments

    def _update_trust_history(self, agents: Dict[str, Agent]) -> None:
        """Track trust score history for drift detection."""
        for agent_id, agent in agents.items():
            if agent_id not in self.trust_history:
                self.trust_history[agent_id] = []
            self.trust_history[agent_id].append(agent.trust_score)

            # Keep only recent history (last 10 cycles)
            if len(self.trust_history[agent_id]) > 10:
                self.trust_history[agent_id] = self.trust_history[agent_id][-10:]

    def _detect_drift(self) -> None:
        """
        Claim 4: Preemptive drift-based decision making.

        Detects when agent trust declines by Δ > threshold across consecutive cycles.
        Formula: drift_detected = ∃i : trust_{i+1} - trust_i < -Δ_threshold
        """
        for agent_id, history in self.trust_history.items():
            if len(history) >= 2:
                delta = history[-1] - history[-2]

                if delta < -self.DRIFT_DETECTION_DELTA:
                    # Drift detected - mark for reduced allocation
                    self.drift_warnings[agent_id] = True
                    print(f"⚠️  Drift detected: {agent_id} (Δ = {delta:.3f})")
                elif delta > 0 and agent_id in self.drift_warnings:
                    # Recovering from drift
                    print(f"📈 Drift recovery: {agent_id} (Δ = {delta:.3f})")
                    self.drift_warnings[agent_id] = False

    def _filter_agents(
        self,
        agents: Dict[str, Agent],
        threshold: float
    ) -> List[Agent]:
        """
        Filter agents based on trust threshold and suppression status.

        Implements Claim 3: Suppression with redemption cycles.

        Logic:
        - Agents with trust < T_supp are suppressed
        - Suppressed agents monitored for max_redemption_cycles
        - If trust recovers to T_supp within window, agent is restored
        - If not recovered after window, agent is permanently suppressed
        """
        active_agents = []

        for agent_id, agent in agents.items():
            # Check suppression status
            if agent_id in self.suppressed_agents:
                cycles_suppressed = self.suppressed_agents[agent_id]

                # Check if in redemption window
                if cycles_suppressed <= self.MAX_REDEMPTION_CYCLES:
                    # Check if recovered
                    if agent.trust_score >= self.SUPPRESSION_THRESHOLD:
                        print(f"🟢 Redemption: {agent_id} recovered (trust: {agent.trust_score:.2f})")
                        del self.suppressed_agents[agent_id]
                        active_agents.append(agent)
                    else:
                        # Still in redemption window but not recovered
                        self.suppressed_agents[agent_id] += 1
                        print(f"🟡 Suppressed: {agent_id} (redemption: {cycles_suppressed}/{self.MAX_REDEMPTION_CYCLES})")
                else:
                    # Exceeded redemption window
                    print(f"🔴 Permanently suppressed: {agent_id} (failed to recover)")
            else:
                # Not currently suppressed - check if should be
                if agent.trust_score < self.SUPPRESSION_THRESHOLD:
                    # Start suppression
                    self.suppressed_agents[agent_id] = 1
                    print(f"🟡 Suppression initiated: {agent_id} (trust: {agent.trust_score:.2f} < {self.SUPPRESSION_THRESHOLD})")
                elif agent.trust_score >= threshold:
                    # Active and trusted
                    active_agents.append(agent)

        return active_agents

    def _create_assignments(
        self,
        tasks: List[Task],
        active_agents: List[Agent]
    ) -> List[Assignment]:
        """
        Create task assignments with drift-aware weighting.

        Agents showing drift receive fewer tasks (preemptive mitigation).
        """
        assignments = []

        # Create weighted agent pool (reduce allocation for drifting agents)
        weighted_agents = []
        for agent in active_agents:
            if agent.id in self.drift_warnings and self.drift_warnings[agent.id]:
                # Drifting agent: add once (50% allocation)
                weighted_agents.append(agent)
            else:
                # Healthy agent: add twice (100% allocation)
                weighted_agents.extend([agent, agent])

        # Assign tasks using weighted round-robin
        for i, task in enumerate(tasks):
            agent = weighted_agents[i % len(weighted_agents)]
            assignments.append(Assignment(task_id=task.id, agent_id=agent.id))

        return assignments

    def get_agent_status(self, agent_id: str) -> Dict:
        """Get detailed status of an agent for debugging/monitoring."""
        return {
            "trust_history": self.trust_history.get(agent_id, []),
            "is_suppressed": agent_id in self.suppressed_agents,
            "suppression_cycles": self.suppressed_agents.get(agent_id, 0),
            "is_drifting": self.drift_warnings.get(agent_id, False),
            "redemption_remaining": max(0, self.MAX_REDEMPTION_CYCLES - self.suppressed_agents.get(agent_id, 0))
        }