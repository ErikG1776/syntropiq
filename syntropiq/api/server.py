"""
FastAPI Server - Production REST API for Syntropiq

Provides HTTP endpoints for task submission, agent management, governance monitoring,
and a synthetic demo event stream for LIVE mode simulation.

No governance logic is modified.
"""

import asyncio
import random
import uuid
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from syntropiq.core.config import SyntropiqConfig
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.governance.mutation_engine import MutationEngine
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.core.models import Task


# ----------------------------------------------------
# Global State
# ----------------------------------------------------

state_manager: PersistentStateManager = None
agent_registry: AgentRegistry = None
governance_loop: GovernanceLoop = None
mutation_engine: MutationEngine = None
executor: DeterministicExecutor = None
config: SyntropiqConfig = None

demo_stream_task: asyncio.Task | None = None
demo_stream_running: bool = False


# ----------------------------------------------------
# Synthetic Demo Stream
# ----------------------------------------------------

async def synthetic_demo_stream():
    """
    Emits synthetic tasks into the REAL governance loop.

    Every 30 cycles:
        - 10 cycles simulate drift pressure
        - Governance reacts naturally
    """
    global demo_stream_running

    print("🟢 Demo stream started")

    cycle_count = 0

    while demo_stream_running:
        try:
            agents = agent_registry.get_agents_dict()

            if not agents:
                await asyncio.sleep(1)
                continue

            drift_window = (cycle_count % 30) < 10

            if drift_window:
                impact = random.uniform(0.9, 1.0)
                urgency = random.uniform(0.9, 1.0)
                risk = random.uniform(0.9, 1.0)
            else:
                impact = random.uniform(0.3, 0.7)
                urgency = random.uniform(0.3, 0.7)
                risk = random.uniform(0.3, 0.7)

            task = Task(
                id=str(uuid.uuid4()),
                impact=impact,
                urgency=urgency,
                risk=risk,
                metadata={"source": "live_demo_stream"}
            )

            result = governance_loop.execute_cycle(
                tasks=[task],
                agents=agents,
                executor=executor,
                run_id="LIVE_STREAM"
            )

            agent_registry.sync_trust_scores()

            mutation_engine.trust_threshold = result["mutation"]["trust_threshold"]
            mutation_engine.suppression_threshold = result["mutation"]["suppression_threshold"]
            mutation_engine.drift_delta = result["mutation"]["drift_delta"]

            cycle_count += 1

        except Exception as e:
            print(f"Demo stream error: {e}")

        await asyncio.sleep(1)

    print("🔴 Demo stream stopped")


# ----------------------------------------------------
# FastAPI Lifecycle
# ----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global state_manager, agent_registry, governance_loop
    global mutation_engine, executor, config

    config = SyntropiqConfig.from_env()

    print("\n" + "="*60)
    print("🚀 Syntropiq Governance Engine - Starting...")
    print("="*60)

    state_manager = PersistentStateManager(db_path=config.database.db_path)
    agent_registry = AgentRegistry(state_manager)

    # ------------------------------------------------
    # AUTO-SEED DEMO AGENTS (controlled by env var)
    # ------------------------------------------------
    if os.getenv("SYNTROPIQ_DEMO_MODE", "true").lower() == "true":
        existing = agent_registry.list_agents()
        if not existing:
            agent_registry.register_agent("growth", ["risk"], 0.9, "active")
            agent_registry.register_agent("conservative", ["risk"], 0.95, "active")
            agent_registry.register_agent("balanced", ["risk"], 0.92, "active")
            print("🌱 Demo agents auto-registered")

    governance_loop = GovernanceLoop(
        state_manager=state_manager,
        trust_threshold=config.governance.trust_threshold,
        routing_mode=config.governance.routing_mode
    )

    mutation_engine = MutationEngine(
        initial_trust_threshold=config.governance.trust_threshold,
        initial_suppression_threshold=config.governance.suppression_threshold,
        initial_drift_delta=config.governance.drift_detection_delta,
        state_manager=state_manager
    )

    governance_loop.trust_engine.trust_threshold = mutation_engine.trust_threshold
    governance_loop.trust_engine.suppression_threshold = mutation_engine.suppression_threshold
    governance_loop.trust_engine.drift_delta = mutation_engine.drift_delta

    executor = DeterministicExecutor()

    print("✅ Syntropiq Ready\n")

    yield

    print("🛑 Shutting down Syntropiq...")
    state_manager.close()


# ----------------------------------------------------
# FastAPI App
# ----------------------------------------------------

app = FastAPI(
    title="Syntropiq Governance Engine",
    description="Self-governing pre-execution plane for autonomous AI",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "Syntropiq Governance Engine", "status": "operational"}


@app.get("/health")
def health():
    stats = state_manager.get_statistics() if state_manager else {}
    return {"status": "healthy", "governance": stats}


# ----------------------------------------------------
# Demo Stream Control
# ----------------------------------------------------

@app.post("/api/v1/demo-stream/start")
async def start_demo_stream():
    global demo_stream_task, demo_stream_running

    if demo_stream_running:
        return {"status": "already_running"}

    demo_stream_running = True
    demo_stream_task = asyncio.create_task(synthetic_demo_stream())
    return {"status": "started"}


@app.post("/api/v1/demo-stream/stop")
async def stop_demo_stream():
    global demo_stream_running

    demo_stream_running = False
    return {"status": "stopped"}


# ----------------------------------------------------
# Include Existing Routes
# ----------------------------------------------------

from syntropiq.api import routes
app.include_router(routes.router)