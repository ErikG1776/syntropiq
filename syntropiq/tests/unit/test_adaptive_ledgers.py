from __future__ import annotations

import sqlite3

from syntropiq.api.state_manager import PersistentStateManager


def test_lambda_history_chain_and_tamper(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db)

    manager.save_lambda_history({"run_id": "RUN_L", "old_lambda": {"l_cost": 0.25}, "new_lambda": {"l_cost": 0.26}})
    manager.save_lambda_history({"run_id": "RUN_L", "old_lambda": {"l_cost": 0.26}, "new_lambda": {"l_cost": 0.27}})
    assert manager.verify_lambda_chain("RUN_L")["ok"] is True

    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE lambda_history SET payload=? WHERE id=(SELECT id FROM lambda_history WHERE run_id=? ORDER BY timestamp ASC, rowid ASC LIMIT 1)",
            ('{"tampered":true}', "RUN_L"),
        )
        conn.commit()
    assert manager.verify_lambda_chain("RUN_L")["ok"] is False


def test_bayes_and_consensus_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_CHAIN_MODE", "log")
    db = tmp_path / "telemetry.db"
    manager = PersistentStateManager(db_path=db)

    manager.save_bayes_posterior({"run_id": "RUN_B", "alpha": 5, "beta": 2, "posterior_mean": 0.71, "posterior_uncertainty": 0.1})
    manager.save_bayes_posterior({"run_id": "RUN_B", "alpha": 6, "beta": 2, "posterior_mean": 0.75, "posterior_uncertainty": 0.09})
    assert manager.verify_bayes_chain("RUN_B")["ok"] is True

    manager.save_consensus_insight({"run_id": "RUN_C", "cycle_id": "RUN_C:1", "consensus_Fs": 0.2, "disagreement": 0.03, "profiles": []})
    manager.save_consensus_insight({"run_id": "RUN_C", "cycle_id": "RUN_C:2", "consensus_Fs": 0.1, "disagreement": 0.05, "profiles": []})
    assert manager.verify_consensus_chain("RUN_C")["ok"] is True
