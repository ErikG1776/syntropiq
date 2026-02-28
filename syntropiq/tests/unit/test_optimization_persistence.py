from __future__ import annotations

import sqlite3

from syntropiq.api.state_manager import PersistentStateManager


def _decision(run_id: str, cycle: int) -> dict:
    return {
        "decision_id": f"{run_id}:{cycle}",
        "run_id": run_id,
        "timestamp": f"2026-02-28T10:00:0{cycle}Z",
        "lambda_vector": {
            "l_cost": 0.25,
            "l_time": 0.25,
            "l_risk": 0.25,
            "l_trust": 0.25,
        },
        "V_prime": {"source": "test"},
        "alignment_score": 88.0,
        "chosen_task_ids": ["task-1"],
        "score_breakdown": {
            "task-1": {
                "score": 0.2,
                "cost": 0.3,
                "time": 0.4,
                "risk": 0.1,
                "trust": 0.7,
            }
        },
    }


def test_save_load_verify_optimization_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_optimization_event(_decision("RUN_OPT", 1))
    manager.save_optimization_event(_decision("RUN_OPT", 2))

    loaded = manager.load_optimization_events("RUN_OPT", limit=10)
    assert len(loaded) == 2
    assert loaded[0]["decision_id"] == "RUN_OPT:1"
    assert loaded[1]["decision_id"] == "RUN_OPT:2"

    verification = manager.verify_optimization_chain("RUN_OPT")
    assert verification["ok"] is True


def test_tamper_detected_in_optimization_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_optimization_event(_decision("RUN_TAMPER", 1))
    manager.save_optimization_event(_decision("RUN_TAMPER", 2))

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE optimization_events SET payload=? WHERE id=(SELECT id FROM optimization_events WHERE run_id=? ORDER BY timestamp ASC, rowid ASC LIMIT 1)",
            ('{"tampered":true}', "RUN_TAMPER"),
        )
        conn.commit()

    verification = manager.verify_optimization_chain("RUN_TAMPER")
    assert verification["ok"] is False
    assert verification["first_bad_index"] is not None
