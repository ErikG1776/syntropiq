from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone

from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager
from syntropiq.api.telemetry import GovernanceTelemetryHub
from syntropiq.core.audit_chain import verify_chain
from syntropiq.core.models import Task
from syntropiq.core.replay import compare_runs, compute_r, load_run_artifacts, replay_run
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.optimize.bayes_posterior import posterior_from_cycles
from syntropiq.optimize.config import (
    get_bayes_mode,
    get_current_lambda,
    get_lambda_adapt_mode,
    get_optimize_mode,
    set_current_lambda,
)
from syntropiq.optimize.lambda_adaptation import compute_adaptive_lambda
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager as RuntimeStateManager
from syntropiq.reflect.config import get_reflect_consensus_mode, get_reflect_mode


def _set_integration_env() -> None:
    os.environ["AUDIT_CHAIN_MODE"] = "log"
    os.environ["OPTIMIZE_MODE"] = "integrate"
    os.environ["OPTIMIZE_LAMBDA_ADAPT_MODE"] = "apply"
    os.environ["OPTIMIZE_BAYES_MODE"] = "apply"
    os.environ["REFLECT_MODE"] = "integrate"
    os.environ["REFLECT_CONSENSUS_MODE"] = "integrate"


# ✅ FIXED TELEMETRY CHAIN VERIFICATION
def _verify_chain_table(db_path: str, table: str, run_id: str) -> bool:
    chain_id = f"telemetry:{run_id}"

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT payload, prev_hash, hash, hash_algo
            FROM {table}
            WHERE chain_id=?
            ORDER BY id ASC
            """,
            (chain_id,),
        ).fetchall()

    row_dicts = [
        {
            "payload": row[0],
            "prev_hash": row[1],
            "hash": row[2],
            "hash_algo": row[3],
        }
        for row in rows
    ]

    if not row_dicts:
        return False

    ok, _, _ = verify_chain(row_dicts)
    return bool(ok)


def run_full_system_demo():
    _set_integration_env()

    run_id = "FULL_SYSTEM_DEMO"
    telemetry_db_path = "full_system_demo.db"
    runtime_db_path = "full_system_demo_runtime.db"

    for path in (telemetry_db_path, runtime_db_path):
        if os.path.exists(path):
            os.remove(path)

    telemetry_state = TelemetryStateManager(db_path=telemetry_db_path)
    telemetry_hub = GovernanceTelemetryHub(
        state_manager=telemetry_state,
        max_events=5000,
        max_cycles=1000,
    )

    runtime_state = RuntimeStateManager(db_path=runtime_db_path)
    registry = AgentRegistry(runtime_state)

    loop = GovernanceLoop(
        state_manager=runtime_state,
        trust_threshold=0.70,
        suppression_threshold=0.75,
        drift_delta=0.10,
        routing_mode="deterministic",
        telemetry=telemetry_hub,
    )

    executor = DeterministicExecutor(
        decision_threshold=-0.05,
        fixed_latency=0.001,
    )

    registry.register_agent("alpha", ["general"], initial_trust_score=0.90, status="active")
    registry.register_agent("beta", ["general"], initial_trust_score=0.85, status="active")
    registry.register_agent("gamma", ["general"], initial_trust_score=0.80, status="active")

    cycles_executed = 0
    deadlock_detected = False
    cycle_mutations = {}

    for i in range(30):
        tasks = [
            Task(id=f"demo-{i}-a", impact=0.80, urgency=0.70, risk=0.20),
            Task(id=f"demo-{i}-b", impact=0.75, urgency=0.65, risk=0.25),
            Task(id=f"demo-{i}-c", impact=0.70, urgency=0.60, risk=0.30),
        ]

        agents = registry.get_agents_dict()

        try:
            result = loop.execute_cycle(
                tasks=tasks,
                agents=agents,
                executor=executor,
                run_id=run_id,
            )
            cycle_mutations[str(result.get("cycle_id"))] = dict(result.get("mutation", {}))
            cycles_executed += 1
        except Exception:
            deadlock_detected = True
            break

        if agents and all(agent.status == "suppressed" for agent in agents.values()):
            deadlock_detected = True
            break

        # Persist adaptive ledgers
        recent_cycles = telemetry_state.load_cycles_by_run_id(run_id, limit=100)

        posterior = posterior_from_cycles(recent_cycles[-50:])
        telemetry_state.save_bayes_posterior({"run_id": run_id, **posterior})

        trust_values = [float(a.trust_score) for a in agents.values()]
        avg_trust = sum(trust_values) / len(trust_values) if trust_values else 0.0

        success_total = sum(int(c.get("successes", 0)) for c in recent_cycles[-10:])
        failure_total = sum(int(c.get("failures", 0)) for c in recent_cycles[-10:])
        denom = success_total + failure_total
        failure_rate = (failure_total / denom) if denom > 0 else 0.0

        current_lambda = get_current_lambda(run_id)

        recommended, deltas = compute_adaptive_lambda(
            base=current_lambda,
            signals={
                "avg_trust": avg_trust,
                "suppression_active": bool(loop.trust_engine.suppressed_agents),
                "drift_delta": float(loop.trust_engine.drift_delta),
                "r_score_latest": 1.0,
                "A_score": 75.0,
                "failure_rate": failure_rate,
                "bayes_risk_multiplier": float(posterior.get("suggested_risk_multiplier", 1.0)),
            },
            bounds={"max_step": 0.02, "max_trust": 0.3},
        )

        telemetry_state.save_lambda_history(
            {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "old_lambda": current_lambda.as_dict(),
                "new_lambda": recommended.as_dict(),
                "deltas": deltas,
                "posterior": posterior,
            }
        )

        set_current_lambda(recommended, run_id=run_id)

    artifacts = load_run_artifacts(telemetry_state, run_id)

    replayed = replay_run(artifacts, seed=123, mode="light")
    comparison = compare_runs(artifacts, replayed)
    r_score = compute_r(comparison)

    telemetry_ok = (
        _verify_chain_table(telemetry_db_path, "events", run_id)
        and _verify_chain_table(telemetry_db_path, "cycles", run_id)
    )

    optimization_ok = bool(telemetry_state.verify_optimization_chain(run_id).get("ok"))
    lambda_ok = bool(telemetry_state.verify_lambda_chain(run_id).get("ok"))
    bayes_ok = bool(telemetry_state.verify_bayes_chain(run_id).get("ok"))
    insight_ok = bool(telemetry_state.verify_reflect_chain(run_id).get("ok"))
    consensus_ok = bool(telemetry_state.verify_consensus_chain(run_id).get("ok"))

    print("\n=== FULL SYSTEM CERTIFICATION ===")
    print(f"run_id: {run_id}")
    print(f"cycles_executed: {cycles_executed}")
    print(f"r_score: {r_score:.6f}")
    print("chains:")
    print(f"  telemetry: {telemetry_ok}")
    print(f"  optimization: {optimization_ok}")
    print(f"  lambda_history: {lambda_ok}")
    print(f"  bayes_posteriors: {bayes_ok}")
    print(f"  insight_ledger: {insight_ok}")
    print(f"  consensus_ledger: {consensus_ok}")
    print(f"suppression_deadlock: {deadlock_detected}")
    print("flags:")
    print(f"  OPTIMIZE_MODE={get_optimize_mode()}")
    print(f"  OPTIMIZE_LAMBDA_ADAPT_MODE={get_lambda_adapt_mode()}")
    print(f"  OPTIMIZE_BAYES_MODE={get_bayes_mode()}")
    print(f"  REFLECT_MODE={get_reflect_mode()}")
    print(f"  REFLECT_CONSENSUS_MODE={get_reflect_consensus_mode()}")

    all_chains_ok = telemetry_ok and optimization_ok and lambda_ok and bayes_ok and insight_ok and consensus_ok
    success = (r_score >= 0.99) and all_chains_ok and (not deadlock_detected)

    print(f"certified: {success}")
    return success


if __name__ == "__main__":
    ok = run_full_system_demo()
    sys.exit(0 if ok else 1)