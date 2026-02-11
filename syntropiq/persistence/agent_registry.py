"""
Agent Registry - Agent Lifecycle Management

Manages agent registration, trust score persistence, and lifecycle operations.
Connects agents to the database for trust score continuity across restarts.
"""

from typing import List, Dict, Optional
from syntropiq.core.models import Agent
from syntropiq.core.exceptions import NoAgentsAvailable, TrustScoreInvalid
from syntropiq.persistence.state_manager import PersistentStateManager


class AgentRegistry:
    """
    Manages agent lifecycle and trust score persistence.
    
    Responsibilities:
    - Register new agents
    - Load trust scores from database
    - Activate/deactivate agents
    - Sync agent state with database
    """
    
    def __init__(self, state_manager: PersistentStateManager):
        """
        Initialize agent registry.
        
        Args:
            state_manager: Database manager for persistence
        """
        self.state = state_manager
        self.agents: Dict[str, Agent] = {}
    
    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        initial_trust_score: float = 0.5,
        status: str = "active"
    ) -> Agent:
        """
        Register a new agent or update existing agent.
        
        Args:
            agent_id: Unique identifier for the agent
            capabilities: List of capabilities (e.g., ["fraud_detection", "risk_analysis"])
            initial_trust_score: Starting trust score (0.0-1.0)
            status: Agent status ("active", "inactive", "suspended")
            
        Returns:
            Registered Agent object
            
        Raises:
            TrustScoreInvalid: If trust score not in [0.0, 1.0]
        """
        if not 0.0 <= initial_trust_score <= 1.0:
            raise TrustScoreInvalid(f"Trust score must be in [0.0, 1.0], got {initial_trust_score}")
        
        # Check if agent already exists in database
        existing_scores = self.state.get_trust_scores()
        
        if agent_id in existing_scores:
            # Agent exists - use database trust score
            trust_score = existing_scores[agent_id]
            print(f"🔄 Agent {agent_id} already registered (trust: {trust_score:.3f})")
        else:
            # New agent - use initial trust score
            trust_score = initial_trust_score
            self.state.update_trust_scores({agent_id: trust_score}, reason="initial_registration")
            print(f"✅ Registered new agent: {agent_id} (trust: {trust_score:.3f})")
        
        # Create agent object
        agent = Agent(
            id=agent_id,
            trust_score=trust_score,
            capabilities=capabilities,
            status=status
        )
        
        self.agents[agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self, status: Optional[str] = None) -> List[Agent]:
        """
        List all agents, optionally filtered by status.
        
        Args:
            status: Filter by status ("active", "inactive", "suspended")
            
        Returns:
            List of agents
        """
        agents = list(self.agents.values())
        
        if status:
            agents = [a for a in agents if a.status == status]
        
        return agents
    
    def get_agents_dict(self, status: Optional[str] = None) -> Dict[str, Agent]:
        """
        Get agents as dictionary (required by governance loop).
        
        Args:
            status: Filter by status
            
        Returns:
            Dictionary of {agent_id: Agent}
        """
        if status:
            return {a.id: a for a in self.list_agents(status=status)}
        return {a.id: a for a in self.list_agents()}
    
    def update_agent_status(self, agent_id: str, status: str):
        """
        Update agent status.
        
        Args:
            agent_id: Agent to update
            status: New status ("active", "inactive", "suspended")
        """
        if agent_id not in self.agents:
            raise NoAgentsAvailable(f"Agent {agent_id} not found in registry")
        
        self.agents[agent_id].status = status
        print(f"🔄 Agent {agent_id} status → {status}")
    
    def sync_trust_scores(self):
        """
        Sync agent trust scores from database.
        
        Call this after governance cycles to refresh agent trust scores.
        """
        db_scores = self.state.get_trust_scores()
        
        for agent_id, trust_score in db_scores.items():
            if agent_id in self.agents:
                self.agents[agent_id].trust_score = trust_score
        
        print(f"🔄 Synced trust scores for {len(db_scores)} agents")
    
    def load_agents_from_defaults(self, default_agents: List[Agent]):
        """
        Load agents from a default list (useful for initialization).
        
        Args:
            default_agents: List of Agent objects to register
        """
        for agent in default_agents:
            self.register_agent(
                agent_id=agent.id,
                capabilities=agent.capabilities,
                initial_trust_score=agent.trust_score,
                status=agent.status
            )
    
    def get_agent_statistics(self) -> Dict:
        """Get agent registry statistics."""
        agents = self.list_agents()
        
        return {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if a.status == "active"]),
            "inactive_agents": len([a for a in agents if a.status == "inactive"]),
            "suspended_agents": len([a for a in agents if a.status == "suspended"]),
            "avg_trust_score": sum(a.trust_score for a in agents) / len(agents) if agents else 0.0,
            "highest_trust": max((a.trust_score for a in agents), default=0.0),
            "lowest_trust": min((a.trust_score for a in agents), default=0.0)
        }
