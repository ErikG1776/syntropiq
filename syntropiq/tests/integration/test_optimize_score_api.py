from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_optimize_score_persists_decision(monkeypatch, tmp_path):
    import syntropiq.api.server as server
    from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager

    monkeypatch.setenv("OPTIMIZE_MODE", "score")
    telemetry_state = TelemetryStateManager(db_path=tmp_path / "telemetry.db")
    agent_registry = SimpleNamespace(
        get_agents_dict=lambda: {
            "alpha": SimpleNamespace(id="alpha", trust_score=0.8, status="active"),
            "beta": SimpleNamespace(id="beta", trust_score=0.6, status="active"),
        }
    )

    with TestClient(server.app) as client:
        monkeypatch.setattr(server, "telemetry_state_manager", telemetry_state)
        monkeypatch.setattr(server, "agent_registry", agent_registry)

        response = client.post(
            "/api/v1/optimize/score",
            json={
                "run_id": "OPT_DEMO_001",
                "tasks": [
                    {"id": "t2", "impact": 0.4, "urgency": 0.4, "risk": 0.8, "metadata": {}},
                    {"id": "t1", "impact": 0.8, "urgency": 0.7, "risk": 0.2, "metadata": {}},
                ],
                "lambda": {
                    "l_cost": 0.25,
                    "l_time": 0.25,
                    "l_risk": 0.25,
                    "l_trust": 0.25,
                },
                "context": {"source": "api_test"},
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["run_id"] == "OPT_DEMO_001"
        assert body["chosen_task_ids"] == ["t1", "t2"]

        events_resp = client.get("/api/v1/optimize/events", params={"run_id": "OPT_DEMO_001", "limit": 10})
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert len(events) == 1
        assert events[0]["decision_id"] == body["decision_id"]

        verify_resp = client.get("/api/v1/optimize/verify", params={"run_id": "OPT_DEMO_001"})
        assert verify_resp.status_code == 200
        verification = verify_resp.json()
        assert verification["ok"] is True
