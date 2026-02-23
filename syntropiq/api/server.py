"""
FastAPI Server - Production REST API for Syntropiq

Provides HTTP endpoints for task submission, agent management, governance monitoring,
and synthetic demo event stream for LIVE mode simulation.
"""

import asyncio
from datetime import datetime, timezone
import os
import random
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from syntropiq.api.telemetry import GovernanceTelemetryHub
from syntropiq.core.config import SyntropiqConfig
from syntropiq.core.models import Task
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.governance.mutation_engine import MutationEngine
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.demo.fraud.data import RealDataPool, generate_fraud_batch
from syntropiq.demo.fraud.executor import FraudDetectionExecutor
from syntropiq.demo.fraud.run import AGENT_PROFILES, DRIFT_AGENT, create_agents


# ----------------------------------------------------
# Global State
# ----------------------------------------------------

state_manager: PersistentStateManager = None
agent_registry: AgentRegistry = None
governance_loop: GovernanceLoop = None
mutation_engine: MutationEngine = None
executor: DeterministicExecutor = None
config: SyntropiqConfig = None
telemetry_hub: GovernanceTelemetryHub = None

demo_stream_task: asyncio.Task | None = None
demo_stream_running: bool = False

fraud_demo_task: asyncio.Task | None = None
fraud_demo_running: bool = False


# ----------------------------------------------------
# Synthetic Demo Stream
# ----------------------------------------------------


async def synthetic_demo_stream():
    """
    Emits high-variance synthetic tasks into the real governance loop.

    Rotating phases:
    - high_performance: strong success bias and recovery runway
    - drift_pressure: unstable mixed outcomes with volatile task profiles
    - failure_burst: intentional underperformance with controlled severe bursts
    """
    global demo_stream_running

    print("🟢 Demo stream started")

    cycle_count = 0
    fully_suppressed_streak = 0

    PHASE_LENGTH = 8
    CYCLE_SLEEP_SECONDS = 1

    while demo_stream_running:
        try:
            agents = agent_registry.get_agents_dict()

            if not agents:
                await asyncio.sleep(CYCLE_SLEEP_SECONDS)
                continue

            # Safety valve: avoid deadlocked demos when every agent remains suppressed.
            if fully_suppressed_streak > 3:
                recovery_target = max(agents.values(), key=lambda a: a.trust_score)
                recovery_target.trust_score = 0.75
                recovery_target.status = "active"
                governance_loop.trust_engine.suppressed_agents.pop(recovery_target.id, None)
                governance_loop.trust_engine.probation_agents.pop(recovery_target.id, None)
                state_manager.update_trust_scores(
                    {recovery_target.id: recovery_target.trust_score},
                    reason="demo_auto_recovery",
                )
                state_manager.update_agent_status(recovery_target.id, "active")
                fully_suppressed_streak = 0
                print(
                    f"[demo] auto-recovery activated -> agent={recovery_target.id} trust=0.750"
                )

            phase_slot = cycle_count % (PHASE_LENGTH * 3)
            phase_cycle = cycle_count % PHASE_LENGTH

            if phase_slot < PHASE_LENGTH:
                phase = "high_performance"
            elif phase_slot < PHASE_LENGTH * 2:
                phase = "drift_pressure"
            else:
                phase = "failure_burst"

            # Phase-specific threshold modulation drives real success/failure dynamics.
            if phase == "high_performance":
                executor.decision_threshold = -0.12
            elif phase == "drift_pressure":
                executor.decision_threshold = random.choice([-0.02, 0.0, 0.06, 0.1])
            else:
                severe_burst = (phase_cycle % 5) in (1, 3)  # ~40% severe cycles in failure window
                executor.decision_threshold = 0.24 if severe_burst else 0.1

            # Track likely authority leader so failures can push suppression events.
            ranked_agents = sorted(agents.values(), key=lambda a: a.trust_score, reverse=True)
            suppress_target = ranked_agents[0].id if ranked_agents else "unknown"

            if phase == "high_performance":
                task_count = random.randint(6, 9)
            elif phase == "drift_pressure":
                task_count = random.randint(5, 11)
            else:
                task_count = random.randint(7, 12)

            tasks = []
            for i in range(task_count):
                if phase == "high_performance":
                    impact = random.uniform(0.65, 1.0)
                    urgency = random.uniform(0.6, 1.0)
                    risk = random.uniform(0.05, 0.32)
                elif phase == "drift_pressure":
                    impact = random.uniform(0.2, 1.0)
                    urgency = random.uniform(0.2, 1.0)
                    # Alternate between safe and risky tasks to generate trust oscillation.
                    risk = random.uniform(0.15, 0.45) if i % 2 == 0 else random.uniform(0.55, 0.95)
                else:
                    severe_burst = (phase_cycle % 5) in (1, 3)
                    if severe_burst:
                        impact = random.uniform(0.8, 1.0)
                        urgency = random.uniform(0.75, 1.0)
                        risk = random.uniform(0.82, 0.99)
                    else:
                        impact = random.uniform(0.45, 0.95)
                        urgency = random.uniform(0.45, 0.95)
                        risk = random.uniform(0.45, 0.9)

                    # Inject low-risk pockets so suppressed agents can recover in later rotations.
                    if i >= task_count - 2:
                        risk = random.uniform(0.12, 0.35)

                tasks.append(
                    Task(
                        id=str(uuid.uuid4()),
                        impact=impact,
                        urgency=urgency,
                        risk=risk,
                        metadata={
                            "source": "live_demo_stream",
                            "phase": phase,
                            "phase_cycle": phase_cycle,
                            "global_cycle": cycle_count,
                            "decision_threshold": executor.decision_threshold,
                            "suppress_target": suppress_target,
                        },
                    )
                )

            result = governance_loop.execute_cycle(
                tasks=tasks,
                agents=agents,
                executor=executor,
                run_id="LIVE_STREAM",
            )

            agent_registry.sync_trust_scores()

            mutation_engine.trust_threshold = result["mutation"]["trust_threshold"]
            mutation_engine.suppression_threshold = result["mutation"][
                "suppression_threshold"
            ]
            mutation_engine.drift_delta = result["mutation"]["drift_delta"]

            successes = result["statistics"]["successes"]
            failures = result["statistics"]["failures"]
            fully_suppressed = bool(agents) and all(a.status == "suppressed" for a in agents.values())
            fully_suppressed_streak = fully_suppressed_streak + 1 if fully_suppressed else 0

            print(
                f"[demo] cycle={cycle_count:03d} phase={phase:<16} "
                f"succ={successes} fail={failures} threshold={executor.decision_threshold:.2f} "
                f"target={suppress_target} suppressed_streak={fully_suppressed_streak}"
            )

            cycle_count += 1

        except Exception as e:
            print(f"Demo stream error: {e}")

        await asyncio.sleep(CYCLE_SLEEP_SECONDS)

    print("🔴 Demo stream stopped")


def _fraud_risk_profile(cycle: int, num_cycles: int) -> str:
    if num_cycles <= 0:
        return "mixed"
    pct = cycle / num_cycles
    if pct < 0.20:
        return "mixed"
    if pct < 0.55:
        return "high_risk"
    if pct < 0.75:
        return "low_risk"
    return "mixed"


def _build_fraud_transaction_batches(
    num_cycles: int,
    batch_size: int,
    seed: int,
    csv_path: str | None,
    real_data: bool,
):
    data_pool = None

    if real_data or csv_path:
        try:
            data_pool = RealDataPool(csv_path=csv_path, seed=seed)
            print(f"[fraud-demo] using data source: {data_pool.description}")
        except Exception as err:
            print(f"[fraud-demo] real data unavailable ({err}); falling back to synthetic")
            data_pool = None

    all_txns = []
    for batch_id in range(num_cycles):
        profile = _fraud_risk_profile(batch_id, num_cycles)
        if data_pool:
            all_txns.extend(
                data_pool.sample_batch(batch_size, batch_id=batch_id, risk_profile=profile)
            )
        else:
            all_txns.extend(
                generate_fraud_batch(
                    batch_size,
                    batch_id=batch_id,
                    seed=seed + batch_id,
                    risk_profile=profile,
                )
            )

    return all_txns


def _fallback_emit_fraud_cycle_to_telemetry(
    *,
    run_id: str,
    cycle_id: str,
    timestamp: str,
    trust_before: dict,
    trust_after: dict,
    execution_results: list,
    mutation: dict,
    reflection: dict,
):
    if telemetry_hub is None:
        return

    assignments = {}
    for result in execution_results:
        aid = result.agent_id
        assignments[aid] = assignments.get(aid, 0) + 1

    total_assignments = max(1, len(execution_results))
    total_agents = max(1, len(trust_after))

    authority_before = {aid: 1.0 / total_agents for aid in trust_after.keys()}
    authority_after = {
        aid: assignments.get(aid, 0) / total_assignments for aid in trust_after.keys()
    }

    events = []
    for aid in trust_after.keys():
        before = float(trust_before.get(aid, trust_after.get(aid, 0.0)))
        after = float(trust_after.get(aid, before))
        events.append(
            {
                "run_id": run_id,
                "cycle_id": cycle_id,
                "timestamp": timestamp,
                "type": "trust_update",
                "agent_id": aid,
                "trust_before": round(before, 6),
                "trust_after": round(after, 6),
                "authority_before": round(authority_before.get(aid, 0.0), 6),
                "authority_after": round(authority_after.get(aid, 0.0), 6),
                "metadata": {"fallback": True},
            }
        )

    events.append(
        {
            "run_id": run_id,
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "type": "mutation",
            "agent_id": None,
            "trust_before": 0.0,
            "trust_after": 0.0,
            "authority_before": 0.0,
            "authority_after": 0.0,
            "metadata": {
                "fallback": True,
                "trust_threshold": mutation.get("trust_threshold"),
                "suppression_threshold": mutation.get("suppression_threshold"),
                "drift_delta": mutation.get("drift_delta"),
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
                "fallback": True,
                "constraint_score": reflection.get("constraint_score"),
                "grounded": reflection.get("grounded"),
                "recursive": reflection.get("recursive"),
            },
        }
    )

    telemetry_hub.publish_events(events)
    telemetry_hub.record_cycle(
        {
            "run_id": run_id,
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "total_agents": len(trust_after),
            "successes": sum(1 for r in execution_results if r.success),
            "failures": sum(1 for r in execution_results if not r.success),
            "trust_delta_total": round(
                sum(
                    float(trust_after.get(aid, 0.0)) - float(trust_before.get(aid, 0.0))
                    for aid in trust_after.keys()
                ),
                6,
            ),
            "authority_redistribution": {
                aid: round(
                    authority_after.get(aid, 0.0) - authority_before.get(aid, 0.0),
                    6,
                )
                for aid in trust_after.keys()
            },
            "events": events,
        }
    )


async def fraud_demo_stream():
    """
    Run the existing fraud demo execution pattern as a background stream,
    but execute cycles through the live server governance loop.
    """
    global fraud_demo_running

    print("🟢 Fraud demo stream started")

    num_cycles = int(os.getenv("FRAUD_DEMO_CYCLES", "120"))
    batch_size = int(os.getenv("FRAUD_DEMO_BATCH_SIZE", "8"))
    seed = int(os.getenv("FRAUD_DEMO_SEED", "2024"))
    csv_path = os.getenv("FRAUD_DEMO_CSV")
    real_data = os.getenv("FRAUD_DEMO_REAL_DATA", "false").lower() == "true"

    # Ensure fraud agents exist in the live registry and are active.
    seeded_agents = create_agents()
    for aid, agent in seeded_agents.items():
        if server_agent := agent_registry.get_agent(aid):
            server_agent.status = "active"
            continue
        agent_registry.register_agent(
            agent_id=aid,
            capabilities=agent.capabilities,
            initial_trust_score=agent.trust_score,
            status="active",
        )

    fraud_executor = FraudDetectionExecutor(
        agent_profiles=dict(AGENT_PROFILES),
        drift_agent_id=DRIFT_AGENT,
        drift_rate=0.04,
        drift_start_cycle=3,
    )

    cycle_index = 0

    while fraud_demo_running:
        try:
            all_txns = _build_fraud_transaction_batches(
                num_cycles=num_cycles,
                batch_size=batch_size,
                seed=seed + cycle_index,
                csv_path=csv_path,
                real_data=real_data,
            )

            tx_idx = 0
            for local_cycle in range(num_cycles):
                if not fraud_demo_running:
                    break

                cycle_txns = all_txns[tx_idx : tx_idx + batch_size]
                tx_idx += batch_size
                if not cycle_txns:
                    break

                tasks = [tx.to_task() for tx in cycle_txns]

                live_agents = {
                    aid: agent_registry.get_agent(aid)
                    for aid in create_agents().keys()
                    if agent_registry.get_agent(aid) is not None
                }

                if not live_agents:
                    print("[fraud-demo] no fraud agents available")
                    await asyncio.sleep(1)
                    continue

                # Ensure fraud cycles use the same telemetry pipeline as live synthetic stream.
                governance_loop.telemetry = telemetry_hub
                telemetry_events_before = len(telemetry_hub.get_events_since()) if telemetry_hub else 0
                telemetry_cycles_before = len(telemetry_hub.get_cycles(limit=500)) if telemetry_hub else 0

                trust_before = {aid: float(agent.trust_score) for aid, agent in live_agents.items()}

                result = governance_loop.execute_cycle(
                    tasks=tasks,
                    agents=live_agents,
                    executor=fraud_executor,
                    run_id=f"FRAUD_{cycle_index:06d}",
                )

                # Fallback telemetry emit if loop telemetry did not append this cycle.
                if telemetry_hub is not None:
                    telemetry_events_after = len(telemetry_hub.get_events_since())
                    telemetry_cycles_after = len(telemetry_hub.get_cycles(limit=500))
                    if telemetry_events_after == telemetry_events_before or telemetry_cycles_after == telemetry_cycles_before:
                        trust_after = {aid: float(agent.trust_score) for aid, agent in live_agents.items()}
                        _fallback_emit_fraud_cycle_to_telemetry(
                            run_id=result.get("run_id", f"FRAUD_{cycle_index:06d}"),
                            cycle_id=result.get("cycle_id", f"FRAUD_{cycle_index:06d}:fallback"),
                            timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat()),
                            trust_before=trust_before,
                            trust_after=trust_after,
                            execution_results=result.get("results", []),
                            mutation=result.get("mutation", {}),
                            reflection=result.get("reflection", {}),
                        )

                agent_registry.sync_trust_scores()

                mutation_engine.trust_threshold = result["mutation"]["trust_threshold"]
                mutation_engine.suppression_threshold = result["mutation"][
                    "suppression_threshold"
                ]
                mutation_engine.drift_delta = result["mutation"]["drift_delta"]

                fraud_executor.advance_cycle()
                cycle_index += 1

                await asyncio.sleep(1)

        except Exception as err:
            print(f"[fraud-demo] stream error: {err}")
            await asyncio.sleep(1)

    print("🔴 Fraud demo stream stopped")


# ----------------------------------------------------
# FastAPI Lifecycle
# ----------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global state_manager, agent_registry, governance_loop
    global mutation_engine, executor, config, telemetry_hub

    config = SyntropiqConfig.from_env()

    print("\n" + "=" * 60)
    print("🚀 Syntropiq Governance Engine - Starting...")
    print("=" * 60)

    state_manager = PersistentStateManager(db_path=config.database.db_path)
    agent_registry = AgentRegistry(state_manager)

    telemetry_hub = GovernanceTelemetryHub(
        max_events=int(os.getenv("GOVERNANCE_EVENT_BUFFER_MAX", "2000")),
        max_cycles=int(os.getenv("GOVERNANCE_CYCLE_BUFFER_MAX", "500")),
    )

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
        routing_mode=config.governance.routing_mode,
        telemetry=telemetry_hub,
    )

    mutation_engine = MutationEngine(
        initial_trust_threshold=config.governance.trust_threshold,
        initial_suppression_threshold=config.governance.suppression_threshold,
        initial_drift_delta=config.governance.drift_detection_delta,
        state_manager=state_manager,
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
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
    telemetry_stats = telemetry_hub.stats() if telemetry_hub else {}
    return {"status": "healthy", "governance": stats, "telemetry": telemetry_stats}


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


@app.post("/api/v1/fraud-demo/start")
async def start_fraud_demo_stream():
    global fraud_demo_task, fraud_demo_running

    if fraud_demo_running:
        return {"status": "already_running"}

    fraud_demo_running = True
    fraud_demo_task = asyncio.create_task(fraud_demo_stream())
    return {"status": "started"}


@app.post("/api/v1/fraud-demo/stop")
async def stop_fraud_demo_stream():
    global fraud_demo_running

    fraud_demo_running = False
    return {"status": "stopped"}


# ----------------------------------------------------
# Include Existing Routes
# ----------------------------------------------------

from syntropiq.api import routes

app.include_router(routes.router)
