from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager
from syntropiq.api.telemetry import GovernanceTelemetryHub
from syntropiq.core.exceptions import CircuitBreakerTriggered
from syntropiq.core.models import Task
from syntropiq.core.replay import compare_runs, compute_r, replay_run
from syntropiq.execution.deterministic_executor import DeterministicExecutor
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.optimize.bayes_posterior import posterior_from_cycles
from syntropiq.optimize.config import get_current_lambda, set_current_lambda
from syntropiq.optimize.lambda_adaptation import compute_adaptive_lambda
from syntropiq.optimize.lambda_optimizer import optimize_tasks
from syntropiq.optimize.schema import OptimizeInput
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.persistence.state_manager import PersistentStateManager as RuntimeStateManager
from syntropiq.reflect.consensus import run_consensus_reflect
from syntropiq.reflect.engine import run_reflect


class DriftAwareDeterministicExecutor(DeterministicExecutor):
    def __init__(
        self,
        decision_threshold: float,
        fixed_latency: float,
        drift_agent: str,
        drift_start: int,
        drift_end: int,
        drift_penalty: float = 0.15,
    ):
        super().__init__(decision_threshold=decision_threshold, fixed_latency=fixed_latency)
        self.drift_agent = drift_agent
        self.drift_start = drift_start
        self.drift_end = drift_end
        self.drift_penalty = drift_penalty
        self.current_cycle = 0

    def execute(self, task: Task, agent):
        base = super().execute(task, agent)
        score = agent.trust_score - task.risk

        drift_disabled = self.drift_agent.strip().lower() in {"none", "off", "disabled"}
        in_drift_window = self.drift_start <= self.current_cycle <= self.drift_end
        if (not drift_disabled) and agent.id == self.drift_agent and in_drift_window:
            score -= self.drift_penalty
            success = score >= self.decision_threshold
            base.success = bool(success)
            md = dict(base.metadata or {})
            md.update(
                {
                    "drift_penalty": self.drift_penalty,
                    "drift_window": True,
                    "score": round(score, 6),
                }
            )
            base.metadata = md
        return base


def _set_integration_env(mode: str) -> None:
    mode_value = "integrate" if mode == "integrate" else "score"
    os.environ["OPTIMIZE_MODE"] = mode_value
    os.environ["OPTIMIZE_LAMBDA_ADAPT_MODE"] = "apply"
    os.environ["OPTIMIZE_BAYES_MODE"] = "apply"
    os.environ["REFLECT_MODE"] = mode_value
    os.environ["REFLECT_CONSENSUS_MODE"] = mode_value
    os.environ["INVARIANTS_MODE"] = "log"
    os.environ["AUDIT_CHAIN_MODE"] = "log"
    os.environ["HEALING_MODE"] = "integrate"
    os.environ["HEALING_CRISIS_MIN_CYCLES"] = "5"
    os.environ["HEALING_FS_SLOPE_MIN"] = "0.01"
    os.environ["HEALING_FS_SLOPE_WINDOW"] = "3"
    os.environ["HEALING_POSTERIOR_MEAN_MIN"] = "0.80"
    os.environ["HEALING_POSTERIOR_UNCERT_MAX"] = "0.10"
    os.environ["HEALING_TRUST_STEP"] = "0.02"
    os.environ["HEALING_TRUST_CAP"] = "0.70"


def _phase_for_cycle(cycle_idx: int, drift_start: int, drift_end: int) -> str:
    if cycle_idx <= 5:
        return "baseline"
    if drift_start <= cycle_idx <= drift_end:
        return "drift"
    if cycle_idx <= 20:
        return "recovery"
    return "stabilized"


def _risk_bounds(phase: str) -> tuple[float, float]:
    if phase == "baseline":
        return (0.10, 0.35)
    if phase == "drift":
        return (0.55, 0.90)
    if phase == "recovery":
        return (0.25, 0.65)
    return (0.15, 0.45)


def _build_tasks(run_id: str, cycle_idx: int, batch_size: int, window_minutes: int, seed: int, phase: str) -> List[Task]:
    rng = random.Random(seed + cycle_idx)
    risk_lo, risk_hi = _risk_bounds(phase)

    tasks: List[Task] = []
    for j in range(batch_size):
        impact = rng.uniform(0.45, 0.95)
        urgency = rng.uniform(0.40, 0.95)
        risk = rng.uniform(risk_lo, risk_hi)
        tasks.append(
            Task(
                id=f"{run_id}:task:{cycle_idx:03d}:{j:03d}",
                impact=round(impact, 6),
                urgency=round(urgency, 6),
                risk=round(risk, 6),
                metadata={
                    "drift_phase": phase,
                    "window_minutes": window_minutes,
                    "txn_count": 1000,
                    "cycle_index": cycle_idx,
                },
            )
        )
    return tasks


def _build_tasks_noisy_stability(
    run_id: str,
    cycle_idx: int,
    batch_size: int,
    window_minutes: int,
    seed: int,
) -> List[Task]:
    rng = random.Random(seed + cycle_idx)
    tasks: List[Task] = []
    for j in range(batch_size):
        impact = rng.uniform(0.45, 0.95)
        urgency = rng.uniform(0.40, 0.95)
        # Deterministic mixture: alternating low/high envelopes for broad variance.
        if ((cycle_idx + j) % 2) == 0:
            risk = rng.uniform(0.15, 0.45)
        else:
            risk = rng.uniform(0.55, 0.85)
        tasks.append(
            Task(
                id=f"{run_id}:task:{cycle_idx:03d}:{j:03d}",
                impact=round(impact, 6),
                urgency=round(urgency, 6),
                risk=round(risk, 6),
                metadata={
                    "drift_phase": "noisy_stability",
                    "window_minutes": window_minutes,
                    "txn_count": 1000,
                    "cycle_index": cycle_idx,
                },
            )
        )
    return tasks


def _build_tasks_recovery_biased(
    run_id: str,
    cycle_idx: int,
    batch_size: int,
    window_minutes: int,
    seed: int,
    phase: str,
) -> List[Task]:
    rng = random.Random(seed + cycle_idx)
    if phase == "baseline":
        risk_lo, risk_hi = (0.10, 0.35)
    elif phase == "drift":
        risk_lo, risk_hi = (0.55, 0.90)
    elif phase == "recovery":
        risk_lo, risk_hi = (0.15, 0.45)
    else:
        risk_lo, risk_hi = (0.12, 0.40)

    tasks: List[Task] = []
    for j in range(batch_size):
        impact = rng.uniform(0.45, 0.95)
        urgency = rng.uniform(0.40, 0.95)
        risk = rng.uniform(risk_lo, risk_hi)
        tasks.append(
            Task(
                id=f"{run_id}:task:{cycle_idx:03d}:{j:03d}",
                impact=round(impact, 6),
                urgency=round(urgency, 6),
                risk=round(risk, 6),
                metadata={
                    "drift_phase": phase,
                    "window_minutes": window_minutes,
                    "txn_count": 1000,
                    "cycle_index": cycle_idx,
                    "risk_profile": "recovery_biased",
                },
            )
        )
    return tasks


def _clear_run_prefix(telemetry_db_path: str, run_id: str) -> None:
    if not os.path.exists(telemetry_db_path):
        return
    with sqlite3.connect(telemetry_db_path) as conn:
        for table in (
            "events",
            "cycles",
            "optimization_events",
            "lambda_history",
            "bayes_posteriors",
            "insight_ledger",
            "consensus_insights",
            "replay_validations",
        ):
            try:
                conn.execute(
                    f"DELETE FROM {table} WHERE chain_id LIKE ? OR run_id LIKE ?",
                    (f"{run_id}:%", f"{run_id}%"),
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute(
                    f"DELETE FROM {table} WHERE chain_id = ?",
                    (f"telemetry:{run_id}",),
                )
            except sqlite3.OperationalError:
                pass
        conn.commit()


def _load_cycle_snapshots_from_telemetry(db_path: str, run_prefix: str) -> List[Dict[str, Any]]:
    telemetry_chain_id = f"telemetry:{run_prefix}"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cycles = conn.execute(
            "SELECT payload FROM cycles WHERE chain_id = ? OR chain_id LIKE ? ORDER BY id ASC, rowid ASC",
            (telemetry_chain_id, f"{run_prefix}:%"),
        ).fetchall()
        events = conn.execute(
            "SELECT payload FROM events WHERE chain_id = ? OR chain_id LIKE ? ORDER BY id ASC, rowid ASC",
            (telemetry_chain_id, f"{run_prefix}:%"),
        ).fetchall()

    events_by_cycle: Dict[str, List[Dict[str, Any]]] = {}
    for row in events:
        evt = json.loads(row["payload"])
        cid = str(evt.get("cycle_id", ""))
        events_by_cycle.setdefault(cid, []).append(evt)

    snapshots: List[Dict[str, Any]] = []
    for row in cycles:
        cyc = json.loads(row["payload"])
        cid = str(cyc.get("cycle_id", ""))
        cycle_events = events_by_cycle.get(cid, [])

        selected_agents: List[str] = []
        trust_after: Dict[str, float] = {}
        mutation = {
            "trust_threshold": None,
            "suppression_threshold": None,
            "drift_delta": None,
        }
        suppressed_agents: List[str] = []

        for evt in cycle_events:
            et = evt.get("type")
            md = evt.get("metadata") or {}
            if et == "trust_update" and isinstance(evt.get("agent_id"), str):
                trust_after[evt["agent_id"]] = float(evt.get("trust_after", 0.0))
            if et == "mutation":
                mutation["trust_threshold"] = md.get("trust_threshold_after")
                mutation["suppression_threshold"] = md.get("suppression_threshold_after")
                mutation["drift_delta"] = md.get("drift_delta_after")
            if et == "suppression" and isinstance(evt.get("agent_id"), str):
                suppressed_agents.append(evt["agent_id"])

        trust_updates = [evt for evt in cycle_events if evt.get("type") == "trust_update" and isinstance(evt.get("agent_id"), str)]
        if trust_updates:
            selected_agents = sorted({evt["agent_id"] for evt in trust_updates})

        snapshots.append(
            {
                "cycle_id": cid,
                "selected_agents": selected_agents,
                "suppressed_agents": sorted(set(suppressed_agents)),
                "trust_after": trust_after,
                "mutation": {
                    "trust_threshold": float(mutation["trust_threshold"] if mutation["trust_threshold"] is not None else 0.0),
                    "suppression_threshold": float(mutation["suppression_threshold"] if mutation["suppression_threshold"] is not None else 0.0),
                    "drift_delta": float(mutation["drift_delta"] if mutation["drift_delta"] is not None else 0.0),
                },
            }
        )
    return snapshots


def run_investor_demo(args: argparse.Namespace) -> bool:
    _set_integration_env(args.mode)

    telemetry_db_path = "syntropiq_telemetry.db"
    runtime_db_path = "investor_demo_runtime.db"

    _clear_run_prefix(telemetry_db_path, args.run_id)

    telemetry_state = TelemetryStateManager(db_path=telemetry_db_path)
    telemetry_hub = GovernanceTelemetryHub(state_manager=telemetry_state, max_events=10000, max_cycles=3000)

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
    executor = DriftAwareDeterministicExecutor(
        decision_threshold=0.05,
        fixed_latency=0.001,
        drift_agent=args.drift_agent,
        drift_start=args.drift_start,
        drift_end=args.drift_end,
        drift_penalty=float(getattr(args, "drift_penalty", 0.15)),
    )

    registry.register_agent("alpha", ["fraud", "risk"], initial_trust_score=0.90, status="active")
    registry.register_agent("beta", ["fraud", "risk"], initial_trust_score=0.82, status="active")
    registry.register_agent("gamma", ["fraud", "risk"], initial_trust_score=0.84, status="active")

    now = datetime.now(timezone.utc)
    cycle_rows: List[Dict[str, Any]] = []
    consecutive_breakers = 0
    suppression_deadlock = False

    for cycle_idx in range(1, args.cycles + 1):
        executor.current_cycle = cycle_idx
        phase = _phase_for_cycle(cycle_idx, args.drift_start, args.drift_end)
        cycle_run_id = f"{args.run_id}:{cycle_idx:03d}"

        risk_profile = str(getattr(args, "risk_profile", "phased"))
        if risk_profile == "noisy_mixture":
            tasks = _build_tasks_noisy_stability(
                run_id=args.run_id,
                cycle_idx=cycle_idx,
                batch_size=args.batch_size,
                window_minutes=args.window_minutes,
                seed=args.seed,
            )
        elif risk_profile == "recovery_biased":
            tasks = _build_tasks_recovery_biased(
                run_id=args.run_id,
                cycle_idx=cycle_idx,
                batch_size=args.batch_size,
                window_minutes=args.window_minutes,
                seed=args.seed,
                phase=phase,
            )
        else:
            tasks = _build_tasks(
                run_id=args.run_id,
                cycle_idx=cycle_idx,
                batch_size=args.batch_size,
                window_minutes=args.window_minutes,
                seed=args.seed,
                phase=phase,
            )

        agents = registry.get_agents_dict()

        # Explicit optimize scoring and ledger (real objective, no hardcoded outputs).
        current_lambda = get_current_lambda(args.run_id)
        opt_input = OptimizeInput(
            tasks=tasks,
            trust_by_agent={aid: float(agent.trust_score) for aid, agent in agents.items()},
            context={"V_prime": {"cycle": cycle_idx, "phase": phase}},
            request_id=f"{args.run_id}:{cycle_idx:03d}",
        )
        opt_decision = optimize_tasks(opt_input, current_lambda, run_id=args.run_id)
        telemetry_state.save_optimization_event(opt_decision.to_dict())

        try:
            result = loop.execute_cycle(
                tasks=tasks,
                agents=agents,
                executor=executor,
                run_id=cycle_run_id,
            )
            circuit_breaker_triggered = False
        except CircuitBreakerTriggered as e:
            circuit_breaker_triggered = True

            print(f"⚠️ CIRCUIT BREAKER TRIGGERED at cycle {cycle_idx}: {str(e)}")

            result = {
                "run_id": cycle_run_id,
                "tasks_executed": 0,
                "successes": 0,
                "failures": 0,
                "trust_updates": {},
                "mutation": {
                    "trust_threshold": loop.mutation_engine.trust_threshold,
                    "suppression_threshold": loop.mutation_engine.suppression_threshold,
                    "drift_delta": loop.mutation_engine.drift_delta,
                },
                "reflection": None,
                "mediation": {
                    "selected_agents": [],
                    "eligible_agents": [],
                    "selection_strategy": "circuit_breaker",
                },
            }

        selected_agents = sorted({r.agent_id for r in result.get("results", [])})
        if not selected_agents:
            selected_agents = sorted(result.get("mediation", {}).get("selected_agents", []) or [])
        trust_now = {aid: round(float(agent.trust_score), 6) for aid, agent in agents.items()}
        suppressed = sorted(list(getattr(loop.trust_engine, "suppressed_agents", {}).keys()))
        if circuit_breaker_triggered:
            consecutive_breakers += 1
        else:
            consecutive_breakers = 0

        if consecutive_breakers >= 3:
            suppression_deadlock = True

        # Adaptive lambda + posterior ledgers for base run id.
        recent_cycles = telemetry_state.load_cycles_by_run_id(cycle_run_id, limit=1)
        # Aggregate failures via prefix query from telemetry DB.
        with sqlite3.connect(telemetry_db_path) as conn:
            rows = conn.execute(
                "SELECT payload FROM cycles WHERE chain_id LIKE ? ORDER BY timestamp ASC, rowid ASC",
                (f"{args.run_id}:%",),
            ).fetchall()
        all_prefix_cycles = [json.loads(row[0]) for row in rows]

        posterior = posterior_from_cycles(all_prefix_cycles[-50:])
        telemetry_state.save_bayes_posterior({"run_id": args.run_id, **posterior})

        success_total = sum(int(c.get("successes", 0)) for c in all_prefix_cycles[-10:])
        fail_total = sum(int(c.get("failures", 0)) for c in all_prefix_cycles[-10:])
        denom = success_total + fail_total
        failure_rate = (fail_total / denom) if denom > 0 else 0.0

        adapt_signals = {
            "avg_trust": sum(trust_now.values()) / max(1, len(trust_now)),
            "suppression_active": bool(suppressed),
            "drift_delta": float(result["mutation"]["drift_delta"]),
            "r_score_latest": 1.0,
            "A_score": float(opt_decision.alignment_score),
            "failure_rate": failure_rate,
            "bayes_risk_multiplier": float(posterior.get("suggested_risk_multiplier", 1.0)),
        }
        new_lambda, lambda_deltas = compute_adaptive_lambda(
            base=current_lambda,
            signals=adapt_signals,
            bounds={"max_step": 0.02, "max_trust": 0.3},
        )
        set_current_lambda(new_lambda, run_id=args.run_id)
        telemetry_state.save_lambda_history(
            {
                "run_id": args.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "old_lambda": current_lambda.as_dict(),
                "new_lambda": new_lambda.as_dict(),
                "deltas": lambda_deltas,
                "signals": adapt_signals,
            }
        )

        # Explicit reflect + consensus (base run id) for unified ledgers.
        reflect_decision = run_reflect(
            run_id=args.run_id,
            cycle_id=f"{args.run_id}:{cycle_idx:03d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            trust_by_agent=trust_now,
            thresholds={
                "trust_threshold": float(result["mutation"]["trust_threshold"]),
                "suppression_threshold": float(result["mutation"]["suppression_threshold"]),
                "drift_delta": float(result["mutation"]["drift_delta"]),
            },
            suppression_active=bool(suppressed),
            recent_cycles=all_prefix_cycles[-20:],
            recent_events=[],
            horizon_steps=5,
            theta=0.10,
            weights_decay=0.85,
            mode="integrate",
            latest_replay_score=None,
        )
        if circuit_breaker_triggered:
            reflect_decision.classification = "crisis"
            reflect_decision.Fs = min(-0.5, float(reflect_decision.Fs))
        telemetry_state.save_reflect_decision(reflect_decision.to_dict())

        consensus = run_consensus_reflect(
            run_id=args.run_id,
            cycle_id=f"{args.run_id}:{cycle_idx:03d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            trust_by_agent=trust_now,
            thresholds={
                "trust_threshold": float(result["mutation"]["trust_threshold"]),
                "suppression_threshold": float(result["mutation"]["suppression_threshold"]),
                "drift_delta": float(result["mutation"]["drift_delta"]),
            },
            suppression_active=bool(suppressed),
            recent_cycles=all_prefix_cycles[-20:],
            recent_events=[],
            horizon_steps=5,
            theta=0.10,
            latest_replay_score=None,
        )
        telemetry_state.save_consensus_insight(
            {
                "run_id": args.run_id,
                "cycle_id": f"{args.run_id}:{cycle_idx:03d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **consensus,
            }
        )

        cycle_snapshot = {
            "cycle_index": cycle_idx,
            "window_start": (now + timedelta(minutes=args.window_minutes * (cycle_idx - 1))).isoformat(),
            "phase": phase,
            "circuit_breaker": circuit_breaker_triggered,
            "selected_agents": selected_agents,
            "trust": trust_now,
            "suppressed_agents": suppressed,
            "thresholds": {
                "trust_threshold": float(result["mutation"]["trust_threshold"]),
                "suppression_threshold": float(result["mutation"]["suppression_threshold"]),
                "drift_delta": float(result["mutation"]["drift_delta"]),
            },
            "lambda": new_lambda.as_dict(),
            "bayes": posterior,
            "Fs": float(reflect_decision.Fs),
            "classification": reflect_decision.classification,
            "consensus_Fs": float(consensus["consensus_Fs"]),
            "consensus_disagreement": float(consensus["disagreement"]),
        }
        cycle_rows.append(cycle_snapshot)

        print(
            f"[{cycle_idx:02d}/{args.cycles}] phase={phase:<10} selected={','.join(selected_agents) or '-':<10} "
            f"trust(a/b/g)={trust_now.get('alpha',0):.3f}/{trust_now.get('beta',0):.3f}/{trust_now.get('gamma',0):.3f} "
            f"lambda(r/t)={new_lambda.l_risk:.3f}/{new_lambda.l_trust:.3f} "
            f"Fs={reflect_decision.Fs:.3f}({reflect_decision.classification}) "
            f"suppressed={suppressed if suppressed else '[]'}"
        )

    # Replay validation from persisted telemetry prefix artifacts.
    replay_cycles = _load_cycle_snapshots_from_telemetry(telemetry_db_path, args.run_id)
    original = {"run_id": args.run_id, "cycles": replay_cycles}
    replayed = replay_run({"run_id": args.run_id, "cycles": replay_cycles, "mode_capabilities": {}}, seed=args.seed, mode="light")
    r_score = compute_r(compare_runs(original, replayed))

    chains = {
        "telemetry": bool(telemetry_state.verify_events_chain(f"telemetry:{args.run_id}").get("ok"))
        and bool(telemetry_state.verify_cycles_chain(f"telemetry:{args.run_id}").get("ok")),
        "optimization": bool(telemetry_state.verify_optimization_chain(args.run_id).get("ok")),
        "lambda_history": bool(telemetry_state.verify_lambda_chain(args.run_id).get("ok")),
        "bayes_posteriors": bool(telemetry_state.verify_bayes_chain(args.run_id).get("ok")),
        "insight_ledger": bool(telemetry_state.verify_reflect_chain(args.run_id).get("ok")),
        "consensus_ledger": bool(telemetry_state.verify_consensus_chain(args.run_id).get("ok")),
    }

    certified = (
        r_score >= 0.99
        and all(chains.values())
        and not suppression_deadlock
    )

    artifact = {
        "run_id": args.run_id,
        "window_minutes": args.window_minutes,
        "txn_count_per_cycle": 1000,
        "cycles": cycle_rows,
        "final": {
            "r_score": r_score,
            "chains": chains,
            "suppression_deadlock": suppression_deadlock,
            "certified": certified,
        },
    }

    output_path = Path(args.output_json)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print("\n=== INVESTOR DEMO CERTIFICATION ===")
    print(f"run_id: {args.run_id}")
    print(f"cycles_executed: {len(cycle_rows)}")
    print(f"r_score: {r_score:.6f}")
    print(f"chains_ok: {all(chains.values())}")
    print(f"suppression_deadlock: {suppression_deadlock}")
    print(f"certified: {certified}")
    print(f"output_json: {output_path}")

    return certified


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Investor Demo Runner")
    parser.add_argument("--run-id", default="INVESTOR_DEMO_001")
    parser.add_argument("--cycles", type=int, default=30)
    parser.add_argument("--window-minutes", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260228)
    parser.add_argument("--drift-start", type=int, default=6)
    parser.add_argument("--drift-end", type=int, default=12)
    parser.add_argument("--drift-agent", default="beta")
    parser.add_argument("--drift-penalty", type=float, default=0.15)
    parser.add_argument("--output-json", default="investor_demo_output.json")
    parser.add_argument("--mode", default="integrate")
    parser.add_argument(
        "--risk-profile",
        choices=["phased", "recovery_biased", "noisy_mixture"],
        default="phased",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    ok = run_investor_demo(args)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
