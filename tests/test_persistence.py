from syntropiq.api.state_manager import PersistentStateManager


def test_persistent_state_manager_saves_and_loads_event_and_cycle(tmp_path):
    db_path = tmp_path / "telemetry.db"

    manager = PersistentStateManager(db_path=db_path)
    manager.save_event(
        {
            "id": "evt-1",
            "timestamp": "2026-01-01T00:00:00Z",
            "type": "trust_update",
            "run_id": "RUN_1",
            "cycle_id": "RUN_1:1",
            "agent_id": "agent_a",
            "trust_before": 0.4,
            "trust_after": 0.6,
            "authority_before": 0.4,
            "authority_after": 0.6,
            "metadata": {"source": "test"},
        }
    )
    manager.save_cycle(
        {
            "run_id": "RUN_1",
            "cycle_id": "RUN_1:1",
            "timestamp": "2026-01-01T00:00:00Z",
            "total_agents": 3,
            "successes": 2,
            "failures": 1,
            "trust_delta_total": 0.1,
            "authority_redistribution": {"agent_a": 0.6},
            "events": [],
        }
    )

    reloaded = PersistentStateManager(db_path=db_path)

    events = reloaded.load_recent_events()
    cycles = reloaded.load_recent_cycles()

    assert len(events) == 1
    assert events[0]["id"] == "evt-1"

    assert len(cycles) == 1
    assert cycles[0]["cycle_id"] == "RUN_1:1"
