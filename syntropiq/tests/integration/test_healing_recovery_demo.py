from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_healing_recovery_demo(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    output_path = tmp_path / "healing_demo_output.json"

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing else f"{repo_root}:{existing}"
    env["HEALING_MODE"] = "integrate"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "syntropiq.tools.investor_demo_runner",
            "--run-id",
            "INVESTOR_HEALING_TEST",
            "--cycles",
            "30",
            "--batch-size",
            "10",
            "--drift-agent",
            "alpha",
            "--output-json",
            str(output_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["final"]["r_score"] >= 0.99
    assert payload["final"]["certified"] is True

    cycle_rows = payload["cycles"]
    assert cycle_rows, "expected cycle snapshots"

    recovered = any(
        (row.get("classification") == "stable") or (float(row.get("Fs", -1.0)) >= 0.10)
        for row in cycle_rows
    )
    assert recovered, "expected at least one stable or above-threshold cycle"

    had_suppression = any(bool(row.get("suppressed_agents")) for row in cycle_rows)
    assert had_suppression, "expected suppression during stress period"

    assert not payload["final"]["suppression_deadlock"]
