from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_reflect_api_run_and_verify(monkeypatch, tmp_path):
    import syntropiq.api.server as server
    from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager

    monkeypatch.setenv("REFLECT_MODE", "score")

    telemetry_state = TelemetryStateManager(db_path=tmp_path / "telemetry.db")
    agent_registry = SimpleNamespace(
        get_agents_dict=lambda: {
            "alpha": SimpleNamespace(id="alpha", trust_score=0.82, status="active"),
            "beta": SimpleNamespace(id="beta", trust_score=0.77, status="active"),
        }
    )
    mutation_engine = SimpleNamespace(
        trust_threshold=0.70,
        suppression_threshold=0.75,
        drift_delta=0.10,
    )
    governance_loop = SimpleNamespace(
        trust_engine=SimpleNamespace(suppressed_agents={})
    )

    with TestClient(server.app) as client:
        monkeypatch.setattr(server, "telemetry_state_manager", telemetry_state)
        monkeypatch.setattr(server, "agent_registry", agent_registry)
        monkeypatch.setattr(server, "mutation_engine", mutation_engine)
        monkeypatch.setattr(server, "governance_loop", governance_loop)

        response = client.post(
            "/api/v1/reflect/run",
            json={
                "run_id": "EXEC_GATEWAY",
                "cycle_id": "EXEC_GATEWAY:1",
                "horizon_steps": 5,
                "theta": 0.10,
                "weights_decay": 0.85,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "Fs" in payload
        assert payload["classification"] in {"stable", "degrading", "crisis"}

        decisions = client.get(
            "/api/v1/reflect/decisions",
            params={"run_id": "EXEC_GATEWAY", "limit": 10},
        )
        assert decisions.status_code == 200
        rows = decisions.json()
        assert len(rows) == 1

        verify = client.get("/api/v1/reflect/verify", params={"run_id": "EXEC_GATEWAY"})
        assert verify.status_code == 200
        assert verify.json()["ok"] is True
