from __future__ import annotations

import argparse
import sys

from syntropiq.api.state_manager import PersistentStateManager
from syntropiq.core.replay import compare_runs, compute_r, load_run_artifacts, replay_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay reproducibility check")
    parser.add_argument("--run-id", required=True, help="Run identifier to validate")
    parser.add_argument("--threshold", type=float, default=0.99, help="Minimum acceptable r score")
    parser.add_argument("--seed", type=int, default=None, help="Optional replay seed")
    parser.add_argument("--mode", choices=["light", "full"], default="light", help="Replay mode")
    args = parser.parse_args()

    manager = PersistentStateManager()
    artifacts = load_run_artifacts(manager, args.run_id)

    if not artifacts.get("cycles"):
        print(f"missing artifacts for run_id={args.run_id}")
        return 2

    replayed = replay_run(artifacts, seed=args.seed, mode=args.mode)
    comparison = compare_runs(artifacts, replayed)
    r_score = compute_r(comparison)

    print(f"run_id={args.run_id} mode={replayed.get('mode')} r={r_score:.6f} threshold={args.threshold:.6f}")
    print(
        "components="
        f"selection={comparison.selection_match:.6f},"
        f"trust={comparison.trust_corr:.6f},"
        f"threshold={comparison.threshold_corr:.6f},"
        f"suppression={comparison.suppression_match:.6f}"
    )

    if r_score >= args.threshold:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
