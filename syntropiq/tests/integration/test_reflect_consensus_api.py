from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_reflect_consensus_endpoint(monkeypatch, tmp_path):
    import syntropiq.api.server as server
    from syntropiq.api.state_manager import PersistentStateManager as TelemetryStateManager

    monkeypatch.setenv("REFLECT_MODE", "score")
    monkeypatch.setenv("REFLECT_CONSENSUS_MODE", "log")

    telemetry_state = TelemetryStateManager(db_path=tmp_path / "telemetry.db")
    telemetry_state.save_cycle({
        "run_id": "RUN_REF_C",
        "cycle_id": "RUN_REF_C:1",
        "timestamp": "2026-02-28T12:00:00Z",
        "total_agents": 2,
        "successes": 2,
        "failures": 1,
        "trust_delta_total": 0.01,
        "authority_redistribution": {},
        "events": [],
    })

    agent_registry = SimpleNamespace(
        get_agents_dict=lambda: {
            "alpha": SimpleNamespace(id="alpha", trust_score=0.82, status="active"),
            "beta": SimpleNamespace(id="beta", trust_score=0.78, status="active"),
        }
    )
    mutation_engine = SimpleNamespace(trust_threshold=0.7, suppression_threshold=0.75, drift_delta=0.1)
    governance_loop = SimpleNamespace(trust_engine=SimpleNamespace(suppressed_agents={}))

    with TestClient(server.app) as client:
        monkeypatch.setattr(server, "telemetry_state_manager", telemetry_state)
        monkeypatch.setattr(server, "agent_registry", agent_registry)
        monkeypatch.setattr(server, "mutation_engine", mutation_engine)
        monkeypatch.setattr(server, "governance_loop", governance_loop)

        resp = client.post(
            "/api/v1/reflect/consensus",
            json={"run_id": "RUN_REF_C", "cycle_id": "RUN_REF_C:1", "horizon_steps": 5, "theta": 0.1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "consensus_Fs" in body
        assert "profiles" in body

        rows = client.get("/api/v1/reflect/consensus/decisions", params={"run_id": "RUN_REF_C", "limit": 10})
        assert rows.status_code == 200
        assert len(rows.json()) >= 1

        verify = client.get("/api/v1/reflect/consensus/verify", params={"run_id": "RUN_REF_C"})
        assert verify.status_code == 200
        assert verify.json()["ok"] is True
