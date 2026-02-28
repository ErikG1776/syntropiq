from __future__ import annotations

from syntropiq.core.invariants import Invariants, emit_violations


class MockTelemetryHub:
    def __init__(self):
        self.events = []

    def publish_event(self, event):
        self.events.append(event)


def test_tau_bounds_violation():
    violations = Invariants.check_tau_range(0.2)
    assert len(violations) == 1
    assert violations[0].name == "tau_range"


def test_delta_bound_violation():
    violations = Invariants.check_delta_bound(0.2, max_abs=0.05)
    assert len(violations) == 1
    assert violations[0].name == "delta_bound"


def test_gamma_eta_violation():
    violations = Invariants.check_gamma_eta(gamma=0.02, eta=0.02)
    assert len(violations) == 1
    assert violations[0].name == "gamma_eta"


def test_emit_violations_publishes_system_alert(monkeypatch):
    monkeypatch.setenv("INVARIANTS_MODE", "log")
    hub = MockTelemetryHub()
    violations = Invariants.check_tau_range(1.2)

    emit_violations(
        hub,
        violations,
        base_metadata={
            "run_id": "RUN_1",
            "cycle_id": "RUN_1:1",
            "timestamp": "2026-02-28T00:00:00Z",
            "request_id": "req-1",
        },
    )

    assert len(hub.events) == 1
    event = hub.events[0]
    assert event["type"] == "system_alert"
    assert event["metadata"]["invariant"] == "tau_range"
    assert event["metadata"]["request_id"] == "req-1"


def test_emit_violations_off_mode_no_events(monkeypatch):
    monkeypatch.setenv("INVARIANTS_MODE", "off")
    hub = MockTelemetryHub()
    violations = Invariants.check_tau_range(1.2)

    emit_violations(hub, violations, base_metadata={"run_id": "RUN_1"})

    assert hub.events == []
