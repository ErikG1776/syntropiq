import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any


DB_PATH = Path("syntropiq_telemetry.db")


class PersistentStateManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                type TEXT,
                payload TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cycles (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                payload TEXT
            )
            """)

            conn.commit()

    def save_event(self, event: Dict[str, Any]):
        # Use existing id if present
        event_id = event.get("id")

        # Generate deterministic id if missing
        if not event_id:
            cycle_id = event.get("cycle_id") or "no_cycle"
            event_type = event.get("type") or "unknown"
            agent_id = event.get("agent_id") or "none"
            timestamp = event.get("timestamp") or "no_ts"
            event_id = f"{cycle_id}:{event_type}:{agent_id}:{timestamp}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO events (id, timestamp, type, payload) VALUES (?, ?, ?, ?)",
                (
                    event_id,
                    event.get("timestamp"),
                    event.get("type"),
                    json.dumps(event),
                ),
            )
            conn.commit()

    def save_cycle(self, cycle: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cycles (id, timestamp, payload) VALUES (?, ?, ?)",
                (
                    cycle.get("cycle_id") or cycle.get("id"),
                    cycle.get("timestamp"),
                    json.dumps(cycle),
                ),
            )
            conn.commit()

    def load_recent_events(self, limit: int = 500) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in reversed(rows)]

    def load_recent_cycles(self, limit: int = 100) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM cycles ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in reversed(rows)]