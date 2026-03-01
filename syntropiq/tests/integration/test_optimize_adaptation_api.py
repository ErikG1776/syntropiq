from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_optimize_lambda_recommend_apply_history_and_bayes(monkeypatch, tmp_path):
    import syntropiq.api.server as server
    from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager

    monkeypatch.setenv("OPTIMIZE_MODE", "score")
    monkeypatch.setenv("OPTIMIZE_LAMBDA_ADAPT_MODE", "apply")
    monkeypatch.setenv("OPTIMIZE_BAYES_MODE", "log")

    telemetry_state = TelemetryStateManager(db_path=tmp_path / "telemetry.db")
    telemetry_state.save_cycle({
        "run_id": "RUN_OPT_A",
        "cycle_id": "RUN_OPT_A:1",
        "timestamp": "2026-02-28T12:00:00Z",
        "total_agents": 2,
        "successes": 3,
        "failures": 1,
        "trust_delta_total": 0.01,
        "authority_redistribution": {},
        "events": [],
    })

    agent_registry = SimpleNamespace(
        get_agents_dict=lambda: {
            "a": SimpleNamespace(id="a", trust_score=0.85, status="active"),
            "b": SimpleNamespace(id="b", trust_score=0.80, status="active"),
        }
    )

    mutation_engine = SimpleNamespace(drift_delta=0.1, suppression_threshold=0.75)

    with TestClient(server.app) as client:
        monkeypatch.setattr(server, "telemetry_state_manager", telemetry_state)
        monkeypatch.setattr(server, "agent_registry", agent_registry)
        monkeypatch.setattr(server, "mutation_engine", mutation_engine)

        rec = client.post(
            "/api/v1/optimize/lambda/recommend",
            json={"run_id": "RUN_OPT_A", "signals": {"avg_trust": 0.9, "A_score": 80, "drift_delta": 0.05}},
        )
        assert rec.status_code == 200
        assert "new_lambda" in rec.json()

        app = client.post(
            "/api/v1/optimize/lambda/apply",
            json={"run_id": "RUN_OPT_A", "signals": {"avg_trust": 0.9, "A_score": 80, "drift_delta": 0.05}},
        )
        assert app.status_code == 200

        history = client.get("/api/v1/optimize/lambda/history", params={"run_id": "RUN_OPT_A", "limit": 10})
        assert history.status_code == 200
        assert len(history.json()) >= 2

        bayes = client.get("/api/v1/optimize/bayes", params={"run_id": "RUN_OPT_A", "window": 10})
        assert bayes.status_code == 200
        assert "posterior_mean" in bayes.json()

        verify = client.get("/api/v1/optimize/lambda/verify", params={"run_id": "RUN_OPT_A"})
        assert verify.status_code == 200
        assert verify.json()["ok"] is True
