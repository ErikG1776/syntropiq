from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


def test_internal_validation_runner_smoke(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "validation_artifacts"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "syntropiq.tools.internal_validation_runner",
            "--run-prefix",
            "VALID_SMOKE",
            "--seeds",
            "1",
                "--cycles",
                "30",
            "--batch-size",
            "8",
            "--output-dir",
            str(output_dir),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert (output_dir / "mild_drift").exists()
    assert (output_dir / "severe_adversarial").exists()
    assert (output_dir / "noisy_stability").exists()
    assert list((output_dir / "mild_drift").glob("*.json"))
