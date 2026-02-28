from __future__ import annotations

import sqlite3

from syntropiq.api.state_manager import PersistentStateManager


def _event(run_id: str, cycle_id: str, ts: str, event_type: str = "trust_update"):
    return {
        "run_id": run_id,
        "cycle_id": cycle_id,
        "timestamp": ts,
        "type": event_type,
        "agent_id": "agent_a",
        "trust_before": 0.4,
        "trust_after": 0.5,
        "authority_before": 0.3,
        "authority_after": 0.4,
        "metadata": {"source": "test"},
    }


def _cycle(run_id: str, cycle_id: str, ts: str):
    return {
        "run_id": run_id,
        "cycle_id": cycle_id,
        "timestamp": ts,
        "total_agents": 1,
        "successes": 1,
        "failures": 0,
        "trust_delta_total": 0.1,
        "authority_redistribution": {"agent_a": 0.1},
        "events": [],
    }


def test_event_chain_links_and_verifies(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_event(_event("RUN_A", "RUN_A:1", "2026-02-28T10:00:00Z"))
    manager.save_event(_event("RUN_A", "RUN_A:2", "2026-02-28T10:00:01Z"))

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT prev_hash, hash FROM events WHERE chain_id=? ORDER BY timestamp ASC, rowid ASC",
            ("RUN_A",),
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] is None
    assert rows[1][0] == rows[0][1]

    verification = manager.verify_events_chain(chain_id="RUN_A")
    assert verification["ok"] is True
    assert verification["first_bad_index"] is None


def test_event_chain_detects_tamper(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_event(_event("RUN_T", "RUN_T:1", "2026-02-28T10:00:00Z"))
    manager.save_event(_event("RUN_T", "RUN_T:2", "2026-02-28T10:00:01Z"))

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE events SET payload=? WHERE id=(SELECT id FROM events WHERE chain_id=? ORDER BY timestamp ASC, rowid ASC LIMIT 1)",
            ('{"tampered":true}', "RUN_T"),
        )
        conn.commit()

    verification = manager.verify_events_chain(chain_id="RUN_T")
    assert verification["ok"] is False
    assert verification["first_bad_index"] is not None
    assert verification["reason"] in {"hash_mismatch", "prev_hash_mismatch", "invalid_payload_json", "missing_hash"}


def test_separate_event_chains_do_not_cross_link(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_event(_event("RUN_A", "RUN_A:1", "2026-02-28T10:00:00Z"))
    manager.save_event(_event("RUN_A", "RUN_A:2", "2026-02-28T10:00:01Z"))
    manager.save_event(_event("RUN_B", "RUN_B:1", "2026-02-28T10:00:02Z"))

    with sqlite3.connect(db_path) as conn:
        run_b = conn.execute(
            "SELECT prev_hash FROM events WHERE chain_id=? ORDER BY timestamp ASC, rowid ASC LIMIT 1",
            ("RUN_B",),
        ).fetchone()

    assert run_b is not None
    assert run_b[0] is None


def test_cycle_chain_links_and_verifies(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db_path = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db_path)

    manager.save_cycle(_cycle("RUN_C", "RUN_C:1", "2026-02-28T10:00:00Z"))
    manager.save_cycle(_cycle("RUN_C", "RUN_C:2", "2026-02-28T10:00:01Z"))

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT prev_hash, hash FROM cycles WHERE chain_id=? ORDER BY timestamp ASC, rowid ASC",
            ("RUN_C",),
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] is None
    assert rows[1][0] == rows[0][1]

    verification = manager.verify_cycles_chain(chain_id="RUN_C")
    assert verification["ok"] is True
    assert verification["first_bad_index"] is None
