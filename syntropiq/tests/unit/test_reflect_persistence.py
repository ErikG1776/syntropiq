from __future__ import annotations

import sqlite3

from syntropiq.api.state_manager import PersistentStateManager


def _decision(run_id: str, cycle_id: str, fs: float) -> dict:
    return {
        "id": f"{run_id}:{cycle_id}",
        "run_id": run_id,
        "cycle_id": cycle_id,
        "timestamp": "2026-02-28T12:00:00Z",
        "Fs": fs,
        "classification": "stable" if fs >= 0.1 else "degrading",
        "mode": "score",
        "horizon_steps": 5,
        "weights": {"0": 0.4, "1": 0.3, "2": 0.2, "3": 0.07, "4": 0.03},
        "Fs_threshold": 0.1,
        "penalties": [],
        "foresight": [],
        "advisory": {"recommended_action": "hold", "non_binding": True},
        "metadata": {"source": "test"},
    }


def test_save_load_verify_reflect_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_reflect_decision(_decision("RUN_REF", "RUN_REF:1", 0.2))
    manager.save_reflect_decision(_decision("RUN_REF", "RUN_REF:2", 0.15))

    rows = manager.load_reflect_decisions("RUN_REF", limit=10)
    assert len(rows) == 2
    assert rows[0]["cycle_id"] == "RUN_REF:1"

    verification = manager.verify_reflect_chain("RUN_REF")
    assert verification["ok"] is True


def test_reflect_chain_detects_tamper(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_reflect_decision(_decision("RUN_T", "RUN_T:1", 0.2))
    manager.save_reflect_decision(_decision("RUN_T", "RUN_T:2", 0.1))

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE insight_ledger SET payload=? WHERE id=(SELECT id FROM insight_ledger WHERE run_id=? ORDER BY timestamp ASC, rowid ASC LIMIT 1)",
            ('{"tampered":true}', "RUN_T"),
        )
        conn.commit()

    verification = manager.verify_reflect_chain("RUN_T")
    assert verification["ok"] is False
    assert verification["first_bad_index"] is not None
