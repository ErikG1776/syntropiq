from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_investor_demo_runner_smoke(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    output_path = tmp_path / "investor_demo_output.json"

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing else f"{repo_root}:{existing}"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "syntropiq.tools.investor_demo_runner",
            "--run-id",
            "INVESTOR_DEMO_TEST",
            "--cycles",
            "5",
            "--batch-size",
            "8",
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
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "INVESTOR_DEMO_TEST"
    assert len(payload["cycles"]) == 5
    assert payload["final"]["r_score"] >= 0.99
