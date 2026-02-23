from syntropiq.api.telemetry import GovernanceTelemetryHub


def make_event(ts: str, idx: int):
    return {
        "run_id": "RUN_1",
        "cycle_id": f"RUN_1:{idx}",
        "timestamp": ts,
        "type": "trust_update",
        "agent_id": f"agent_{idx}",
        "trust_before": 0.7,
        "trust_after": 0.8,
        "authority_before": 0.3,
        "authority_after": 0.4,
        "metadata": {"idx": idx},
    }


def test_event_ring_buffer_is_bounded():
    hub = GovernanceTelemetryHub(max_events=2, max_cycles=2)

    hub.publish_event(make_event("2026-01-01T00:00:00Z", 1))
    hub.publish_event(make_event("2026-01-01T00:01:00Z", 2))
    hub.publish_event(make_event("2026-01-01T00:02:00Z", 3))

    events = hub.get_events_since()
    assert len(events) == 2
    assert events[0].cycle_id == "RUN_1:2"
    assert events[1].cycle_id == "RUN_1:3"


def test_get_events_since_filters_correctly():
    hub = GovernanceTelemetryHub(max_events=10, max_cycles=2)

    hub.publish_event(make_event("2026-01-01T00:00:00Z", 1))
    hub.publish_event(make_event("2026-01-01T00:05:00Z", 2))

    filtered = hub.get_events_since("2026-01-01T00:03:00Z")
    assert len(filtered) == 1
    assert filtered[0].cycle_id == "RUN_1:2"
