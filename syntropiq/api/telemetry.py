"""
Governance telemetry primitives (v1).

Provides:
- In-memory ring buffers for events and cycles
- Thread-safe publish/subscribe for SSE clients
- Query helpers for events since timestamp and recent cycles
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import queue
import threading
import uuid
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from syntropiq.api.schemas import GovernanceCycleResponseV1, GovernanceEventV1


def parse_iso_timestamp(value: str) -> datetime:
    """Parse ISO timestamp with optional trailing Z into aware UTC datetime."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class GovernanceTelemetryHub:
    """Thread-safe in-memory telemetry store + stream fanout."""

    def __init__(self, max_events: int = 2000, max_cycles: int = 500):
        self._events: Deque[GovernanceEventV1] = deque(maxlen=max_events)
        self._cycles: Deque[GovernanceCycleResponseV1] = deque(maxlen=max_cycles)
        self._subscribers: Dict[str, queue.Queue[GovernanceEventV1]] = {}
        self._lock = threading.Lock()

    def publish_event(self, event: GovernanceEventV1 | dict) -> GovernanceEventV1:
        payload = (
            event
            if isinstance(event, GovernanceEventV1)
            else GovernanceEventV1.model_validate(event)
        )

        with self._lock:
            self._events.append(payload)
            stale_subscribers: List[str] = []
            for key, subscriber in self._subscribers.items():
                try:
                    subscriber.put_nowait(payload)
                except queue.Full:
                    stale_subscribers.append(key)
            for key in stale_subscribers:
                self._subscribers.pop(key, None)

        return payload

    def publish_events(self, events: Iterable[GovernanceEventV1 | dict]) -> List[GovernanceEventV1]:
        published: List[GovernanceEventV1] = []
        for event in events:
            published.append(self.publish_event(event))
        return published

    def record_cycle(self, cycle: GovernanceCycleResponseV1 | dict) -> GovernanceCycleResponseV1:
        payload = (
            cycle
            if isinstance(cycle, GovernanceCycleResponseV1)
            else GovernanceCycleResponseV1.model_validate(cycle)
        )
        with self._lock:
            self._cycles.append(payload)
        return payload

    def get_events_since(self, since: Optional[str] = None) -> List[GovernanceEventV1]:
        with self._lock:
            events = list(self._events)

        if not since:
            return events

        since_ts = parse_iso_timestamp(since)
        filtered: List[GovernanceEventV1] = []
        for event in events:
            try:
                event_ts = parse_iso_timestamp(event.timestamp)
            except ValueError:
                continue
            if event_ts >= since_ts:
                filtered.append(event)
        return filtered

    def get_cycles(self, limit: int = 20) -> List[GovernanceCycleResponseV1]:
        with self._lock:
            cycles = list(self._cycles)
        bounded_limit = max(1, min(limit, 500))
        return cycles[-bounded_limit:]

    def subscribe(self, max_queue_size: int = 1000) -> Tuple[str, queue.Queue[GovernanceEventV1]]:
        token = str(uuid.uuid4())
        subscriber: queue.Queue[GovernanceEventV1] = queue.Queue(maxsize=max_queue_size)
        with self._lock:
            self._subscribers[token] = subscriber
        return token, subscriber

    def unsubscribe(self, token: str) -> None:
        with self._lock:
            self._subscribers.pop(token, None)

    def stats(self) -> dict:
        with self._lock:
            return {
                "events": len(self._events),
                "cycles": len(self._cycles),
                "subscribers": len(self._subscribers),
            }
