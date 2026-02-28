from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_request_id_header_matches_emitted_event_metadata_request_id(monkeypatch):
    import syntropiq.api.server as server
    import syntropiq.api.routes as routes
    from syntropiq.api.telemetry import GovernanceTelemetryHub

    telemetry = GovernanceTelemetryHub(max_events=100, max_cycles=20)

    agent = SimpleNamespace(id="agent_a", trust_score=0.9, status="active")
    agent_registry = SimpleNamespace(
        get_agents_dict=lambda: {"agent_a": agent},
        sync_trust_scores=lambda: None,
    )

    governance_loop = SimpleNamespace(
        execute_cycle=lambda tasks, agents, executor, run_id: {
            "run_id": run_id,
            "cycle_id": f"{run_id}:1",
            "timestamp": "2026-01-01T00:00:00Z",
            "statistics": {
                "tasks_executed": 1,
                "successes": 1,
                "failures": 0,
                "avg_latency": 0.01,
            },
            "trust_updates": {"agent_a": 0.95},
            "mutation": {
                "trust_threshold": 0.5,
                "suppression_threshold": 0.3,
                "drift_delta": 0.1,
            },
            "reflection": {"summary": "ok"},
        }
    )

    mutation_engine = SimpleNamespace(
        trust_threshold=0.5,
        suppression_threshold=0.3,
        drift_delta=0.1,
    )

    routes.CIRCUIT_STATE["active"] = False
    routes.CIRCUIT_STATE["cooldown_cycles"] = 0

    with TestClient(server.app) as client:
        monkeypatch.setattr(server, "telemetry_hub", telemetry)
        monkeypatch.setattr(server, "agent_registry", agent_registry)
        monkeypatch.setattr(server, "governance_loop", governance_loop)
        monkeypatch.setattr(server, "mutation_engine", mutation_engine)
        monkeypatch.setattr(server, "executor", object())

        response = client.post(
            "/api/v1/governance/execute",
            json={
                "task": {
                    "id": "task-1",
                    "impact": 0.7,
                    "urgency": 0.6,
                    "risk": 0.2,
                    "metadata": {},
                },
                "run_id": "RUN_REQ",
                "strategy": "highest_trust_v1",
            },
        )

    assert response.status_code == 200
    response_request_id = response.headers.get("x-request-id")
    assert response_request_id

    events = telemetry.get_events_since()
    mediation_event = next(e for e in events if e.type.value == "mediation_decision")
    assert mediation_event.metadata.get("request_id") == response_request_id
