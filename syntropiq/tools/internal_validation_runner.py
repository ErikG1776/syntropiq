from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple

from syntropiq.tools.investor_demo_runner import run_investor_demo


BASE_SEED = 20260228


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    drift_agent: str
    drift_start: int
    drift_end: int
    drift_penalty: float
    risk_profile: str


SCENARIOS: List[ScenarioSpec] = [
    ScenarioSpec(
        name="mild_drift",
        drift_agent="alpha",
        drift_start=6,
        drift_end=12,
        drift_penalty=0.08,
        risk_profile="recovery_biased",
    ),
    ScenarioSpec(
        name="severe_adversarial",
        drift_agent="alpha",
        drift_start=3,
        drift_end=15,
        drift_penalty=0.08,
        risk_profile="recovery_biased",
    ),
    ScenarioSpec(
        name="noisy_stability",
        drift_agent="none",
        drift_start=99,
        drift_end=99,
        drift_penalty=0.0,
        risk_profile="noisy_mixture",
    ),
]


@contextmanager
def _pushd(path: Path):
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def _ensure_integrate_env() -> None:
    os.environ["OPTIMIZE_MODE"] = "integrate"
    os.environ["OPTIMIZE_LAMBDA_ADAPT_MODE"] = "apply"
    os.environ["OPTIMIZE_BAYES_MODE"] = "apply"
    os.environ["REFLECT_MODE"] = "integrate"
    os.environ["REFLECT_CONSENSUS_MODE"] = "integrate"
    os.environ["INVARIANTS_MODE"] = "log"
    os.environ["AUDIT_CHAIN_MODE"] = "log"
    os.environ["HEALING_MODE"] = "integrate"


def evaluate_run(output_json: dict, expectations: dict) -> Tuple[bool, List[str]]:
    failures: List[str] = []

    final = output_json.get("final", {})
    cycles = output_json.get("cycles", [])
    chains = final.get("chains", {})
    expected_certified = bool(expectations.get("expected_certified", True))

    if bool(final.get("certified")) != expected_certified:
        failures.append(f"certified expected={expected_certified} actual={final.get('certified')}")

    r_score = float(final.get("r_score", 0.0))
    if r_score < 0.99:
        failures.append(f"r_score below threshold: {r_score:.6f}")

    if not chains or not all(bool(v) for v in chains.values()):
        failures.append(f"chain verification failed: {chains}")

    if bool(final.get("suppression_deadlock", True)):
        failures.append("suppression_deadlock=True")

    if not cycles:
        failures.append("missing cycle snapshots")
        return (len(failures) == 0, failures)

    final_cycle = cycles[-1]
    final_class = str(final_cycle.get("classification", "")).lower()
    final_fs = float(final_cycle.get("Fs", -1.0))
    suppressed_final = list(final_cycle.get("suppressed_agents") or [])
    drift_agent = str(expectations.get("drift_agent", "")).lower()

    if expectations.get("require_final_stable", False):
        if final_class != "stable":
            failures.append(f"final classification not stable: {final_class}")
        if final_fs < float(expectations.get("min_final_fs", 0.0)):
            failures.append(f"final Fs below threshold: {final_fs:.6f}")
        if len(suppressed_final) > 1:
            failures.append(f"too many suppressed agents at end: {suppressed_final}")
        if drift_agent and drift_agent != "none":
            lowered = {str(a).lower() for a in suppressed_final}
            if drift_agent in lowered:
                failures.append(f"drift agent still suppressed at end: {drift_agent}")

    if expectations.get("expect_crisis_or_suppression", False):
        had_crisis = any(str(c.get("classification", "")).lower() == "crisis" for c in cycles)
        had_suppression = any(bool(c.get("suppressed_agents")) for c in cycles)
        if not (had_crisis or had_suppression):
            failures.append("expected at least one crisis or suppression cycle")

    if expectations.get("expect_crisis", False):
        had_crisis = any(str(c.get("classification", "")).lower() == "crisis" for c in cycles)
        if not had_crisis:
            failures.append("expected at least one crisis cycle")

    if expectations.get("max_suppression_cycles") is not None:
        suppression_cycles = sum(1 for c in cycles if bool(c.get("suppressed_agents")))
        max_suppression_cycles = int(expectations["max_suppression_cycles"])
        if suppression_cycles > max_suppression_cycles:
            failures.append(
                f"suppression cycles exceeded: {suppression_cycles} > {max_suppression_cycles}"
            )

    if expectations.get("max_lambda_risk") is not None:
        max_lambda_risk = float(expectations["max_lambda_risk"])
        worst = max(float((c.get("lambda") or {}).get("l_risk", 0.0)) for c in cycles)
        if worst > max_lambda_risk:
            failures.append(f"l_risk runaway: {worst:.6f} > {max_lambda_risk:.6f}")

    return (len(failures) == 0, failures)


def _scenario_expectations(spec: ScenarioSpec) -> dict:
    if spec.name == "mild_drift":
        return {
            "expected_certified": True,
            "require_final_stable": True,
            "min_final_fs": 0.0,
            "drift_agent": spec.drift_agent,
        }
    if spec.name == "severe_adversarial":
        return {
            "expected_certified": True,
            "require_final_stable": True,
            "min_final_fs": 0.0,
            "drift_agent": spec.drift_agent,
        }
    return {
        "expected_certified": True,
        "require_final_stable": True,
        "min_final_fs": 0.0,
        "max_suppression_cycles": 1,
        "max_lambda_risk": 0.70,
    }


def run_internal_validation(args: argparse.Namespace) -> int:
    _ensure_integrate_env()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: List[Dict[str, object]] = []
    all_passed = True

    for spec in SCENARIOS:
        scenario_dir = output_dir / spec.name
        scenario_dir.mkdir(parents=True, exist_ok=True)

        pass_count = 0
        fail_count = 0
        notes: List[str] = []

        for seed_idx in range(args.seeds):
            seed = BASE_SEED + seed_idx
            run_id = f"{args.run_prefix}_{spec.name}_{seed}"
            output_json = scenario_dir / f"{run_id}.json"

            demo_args = SimpleNamespace(
                run_id=run_id,
                cycles=args.cycles,
                window_minutes=args.window_minutes,
                batch_size=args.batch_size,
                seed=seed,
                drift_start=spec.drift_start,
                drift_end=spec.drift_end,
                drift_agent=spec.drift_agent,
                output_json=str(output_json),
                mode="integrate",
                risk_profile=spec.risk_profile,
                drift_penalty=spec.drift_penalty,
            )

            with _pushd(scenario_dir):
                ok = run_investor_demo(demo_args)

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            expected = _scenario_expectations(spec)
            eval_ok, failures = evaluate_run(payload, expected)
            run_ok = bool(ok and eval_ok)

            if run_ok:
                pass_count += 1
            else:
                fail_count += 1
                all_passed = False
                note = f"{run_id}: " + "; ".join(failures or ["runner returned non-zero"])
                notes.append(note)

            if args.verbose:
                print(
                    f"[{spec.name}] seed={seed} run_id={run_id} -> {'PASS' if run_ok else 'FAIL'}"
                )
                if failures:
                    for item in failures:
                        print(f"  - {item}")

        summary.append(
            {
                "scenario": spec.name,
                "seeds": args.seeds,
                "pass": pass_count,
                "fail": fail_count,
                "notes": notes[:3],
            }
        )

    print("\n=== INTERNAL VALIDATION SUMMARY ===")
    print("Scenario | Seeds | Pass | Fail | Notes")
    for row in summary:
        notes = "OK" if not row["notes"] else " | ".join(row["notes"])
        print(f"{row['scenario']} | {row['seeds']} | {row['pass']} | {row['fail']} | {notes}")

    return 0 if all_passed else 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Internal deterministic validation harness")
    parser.add_argument("--run-prefix", default="VALID")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--cycles", type=int, default=30)
    parser.add_argument("--window-minutes", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--output-dir", default="validation_artifacts")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    return run_internal_validation(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
