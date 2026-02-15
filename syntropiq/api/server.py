"""
FastAPI Server - Production REST API for Syntropiq

Provides HTTP endpoints for task submission, agent management, and governance monitoring.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from syntropiq.core.config import SyntropiqConfig
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.governance.mutation_engine import MutationEngine
from syntropiq.execution.deterministic_executor import DeterministicExecutor


# Global state (initialized on startup)
state_manager: PersistentStateManager = None
agent_registry: AgentRegistry = None
governance_loop: GovernanceLoop = None
mutation_engine: MutationEngine = None
executor: DeterministicExecutor = None
config: SyntropiqConfig = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle.
    
    Initializes database, agent registry, and governance components on startup.
    Closes database connection on shutdown.
    """
    global state_manager, agent_registry, governance_loop, mutation_engine, executor, config
    
    # Load configuration
    config = SyntropiqConfig.from_env()
    
    print("\n" + "="*60)
    print("🚀 Syntropiq Governance Engine - Starting...")
    print("="*60)
    
    # Initialize database
    print(f"\n📦 Initializing database: {config.database.db_path}")
    state_manager = PersistentStateManager(db_path=config.database.db_path)
    
    # Initialize agent registry
    print("👥 Initializing agent registry...")
    agent_registry = AgentRegistry(state_manager)
    
    # Initialize governance loop
    print("⚙️  Initializing governance loop...")
    governance_loop = GovernanceLoop(
        state_manager=state_manager,
        trust_threshold=config.governance.trust_threshold,
        routing_mode=config.governance.routing_mode
    )
    
    # Initialize mutation engine
    print("🧬 Initializing mutation engine...")
    mutation_engine = MutationEngine(
        initial_trust_threshold=config.governance.trust_threshold,
        initial_suppression_threshold=config.governance.suppression_threshold,
        initial_drift_delta=config.governance.drift_detection_delta,
        state_manager=state_manager
    )
    governance_loop.trust_engine.trust_threshold = mutation_engine.trust_threshold
    governance_loop.trust_engine.suppression_threshold = mutation_engine.suppression_threshold
    governance_loop.trust_engine.drift_delta = mutation_engine.drift_delta
    
    # Initialize executor (temporary: deterministic executor for testing)
    print("🔧 Initializing executor...")
    executor = DeterministicExecutor()
    
    print(f"\n📡 Routing mode: {config.governance.routing_mode}")
    print("\n" + "="*60)
    print("✅ Syntropiq Ready")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down Syntropiq...")
    state_manager.close()
    print("✅ Shutdown complete\n")


# Create FastAPI app
app = FastAPI(
    title="Syntropiq Governance Engine",
    description="Self-governing pre-execution plane for autonomous AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "Syntropiq Governance Engine",
        "status": "operational",
        "version": "1.0.0",
        "description": "Self-governing pre-execution plane for autonomous AI"
    }


@app.get("/health")
def health():
    """Detailed health check."""
    stats = state_manager.get_statistics() if state_manager else {}
    agent_stats = agent_registry.get_agent_statistics() if agent_registry else {}
    
    return {
        "status": "healthy",
        "database": "connected" if state_manager else "disconnected",
        "governance": stats,
        "agents": agent_stats
    }


# Import routes (will be created next)
from syntropiq.api import routes
app.include_router(routes.router)
