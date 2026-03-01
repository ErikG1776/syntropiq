from types import SimpleNamespace

from syntropiq.api.schemas import ActorSchema, TaskSchema


class _TelemetryStub:
    def __init__(self):
        self.events = []
        self.cycles = []

    def publish_events(self, events):
        self.events.extend(events)

    def record_cycle(self, cycle):
        self.cycles.append(cycle)


def test_governance_execute_emits_actor_in_event_metadata(monkeypatch):
    import syntropiq.api.server as server
    import syntropiq.api.routes as routes

    telemetry = _TelemetryStub()

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

    monkeypatch.setattr(server, "telemetry_hub", telemetry)
    monkeypatch.setattr(server, "agent_registry", agent_registry)
    monkeypatch.setattr(server, "governance_loop", governance_loop)
    monkeypatch.setattr(server, "mutation_engine", mutation_engine)
    monkeypatch.setattr(server, "executor", object())

    routes.CIRCUIT_STATE["active"] = False
    routes.CIRCUIT_STATE["cooldown_cycles"] = 0

    request = routes.GovernanceExecuteRequest(
        task=TaskSchema(
            id="task-1",
            impact=0.7,
            urgency=0.6,
            risk=0.2,
            metadata={},
        ),
        run_id="RUN_ACTOR",
        strategy="highest_trust_v1",
        actor=ActorSchema(user_id="operator@local", role="operator", source="control-plane"),
    )

    response = routes.governance_execute(request)
    assert response["run_id"] == "RUN_ACTOR"

    mediation_event = next(e for e in telemetry.events if e["type"] == "mediation_decision")
    assert mediation_event["metadata"]["actor"]["user_id"] == "operator@local"
    assert mediation_event["metadata"]["actor"]["role"] == "operator"

    mutation_event = next(e for e in telemetry.events if e["type"] == "mutation")
    assert mutation_event["metadata"]["actor"]["user_id"] == "operator@local"
    assert mutation_event["metadata"]["actor"]["source"] == "control-plane"
