import asyncio

from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import syntropiq.api.server as server
from syntropiq.api.routes import stream_events
from syntropiq.api.telemetry import GovernanceTelemetryHub


class _DisconnectingRequest:
    async def is_disconnected(self):
        return True


def test_events_endpoint_returns_events():
    with TestClient(server.app) as client:
        server.telemetry_hub = GovernanceTelemetryHub(max_events=10, max_cycles=10)
        server.telemetry_hub.publish_event(
            {
                "run_id": "RUN_1",
                "cycle_id": "RUN_1:1",
                "timestamp": "2026-01-01T00:00:00Z",
                "type": "trust_update",
                "agent_id": "agent_1",
                "trust_before": 0.7,
                "trust_after": 0.8,
                "authority_before": 0.2,
                "authority_after": 0.3,
                "metadata": {},
            }
        )

        response = client.get("/api/v1/events")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["run_id"] == "RUN_1"


def test_events_sse_route_returns_streaming_response():
    server.telemetry_hub = GovernanceTelemetryHub(max_events=10, max_cycles=10)

    response = asyncio.run(stream_events(_DisconnectingRequest()))
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
