import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from syntropiq.core.audit_chain import compute_hash, derive_chain_id, verify_chain


DB_PATH = Path("syntropiq_telemetry.db")


class PersistentStateManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                type TEXT,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS cycles (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )

            self._migrate_table_columns(
                cursor,
                "events",
                {
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )
            self._migrate_table_columns(
                cursor,
                "cycles",
                {
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS replay_validations (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp TEXT,
                r_score REAL,
                component_scores TEXT,
                ok INTEGER,
                threshold REAL,
                details TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "replay_validations",
                {
                    "run_id": "TEXT",
                    "timestamp": "TEXT",
                    "r_score": "REAL",
                    "component_scores": "TEXT",
                    "ok": "INTEGER",
                    "threshold": "REAL",
                    "details": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS optimization_events (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp TEXT,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "optimization_events",
                {
                    "run_id": "TEXT",
                    "timestamp": "TEXT",
                    "payload": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS insight_ledger (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                cycle_id TEXT,
                timestamp TEXT,
                Fs REAL,
                classification TEXT,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "insight_ledger",
                {
                    "run_id": "TEXT",
                    "cycle_id": "TEXT",
                    "timestamp": "TEXT",
                    "Fs": "REAL",
                    "classification": "TEXT",
                    "payload": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS lambda_history (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp TEXT,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "lambda_history",
                {
                    "run_id": "TEXT",
                    "timestamp": "TEXT",
                    "payload": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS bayes_posteriors (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                timestamp TEXT,
                alpha REAL,
                beta REAL,
                mean REAL,
                uncertainty REAL,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "bayes_posteriors",
                {
                    "run_id": "TEXT",
                    "timestamp": "TEXT",
                    "alpha": "REAL",
                    "beta": "REAL",
                    "mean": "REAL",
                    "uncertainty": "REAL",
                    "payload": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS consensus_insights (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                cycle_id TEXT,
                timestamp TEXT,
                consensus_Fs REAL,
                disagreement REAL,
                payload TEXT,
                chain_id TEXT,
                prev_hash TEXT,
                hash TEXT,
                hash_algo TEXT
            )
            """
            )
            self._migrate_table_columns(
                cursor,
                "consensus_insights",
                {
                    "run_id": "TEXT",
                    "cycle_id": "TEXT",
                    "timestamp": "TEXT",
                    "consensus_Fs": "REAL",
                    "disagreement": "REAL",
                    "payload": "TEXT",
                    "chain_id": "TEXT",
                    "prev_hash": "TEXT",
                    "hash": "TEXT",
                    "hash_algo": "TEXT",
                },
            )

            conn.commit()

    def _migrate_table_columns(self, cursor: sqlite3.Cursor, table: str, columns: Dict[str, str]) -> None:
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        for name, col_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")

    def _audit_chain_mode(self) -> str:
        mode = (os.getenv("AUDIT_CHAIN_MODE") or "log").strip().lower()
        if mode in {"off", "log"}:
            return mode
        return "log"

    def _last_hash_for_chain(self, conn: sqlite3.Connection, table: str, chain_id: str) -> Optional[str]:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT hash FROM {table} WHERE chain_id=? ORDER BY timestamp DESC, rowid DESC LIMIT 1",
            (chain_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return row[0]

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

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id(event, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "events", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, event, algo=hash_algo)

            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (id, timestamp, type, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event.get("timestamp"),
                    event.get("type"),
                    json.dumps(event),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()

    def save_cycle(self, cycle: Dict[str, Any]):
        cycle_id = cycle.get("cycle_id") or cycle.get("id")
        mode = self._audit_chain_mode()
        chain_id = derive_chain_id(cycle, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "cycles", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, cycle, algo=hash_algo)

            conn.execute(
                """
                INSERT OR REPLACE INTO cycles
                (id, timestamp, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    cycle.get("timestamp"),
                    json.dumps(cycle),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
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

    def load_events_by_run_id(self, run_id: str, limit: int = 5000) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM events
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]

    def load_cycles_by_run_id(self, run_id: str, limit: int = 2000) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM cycles
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]

    def save_replay_validation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        payload["id"] = str(payload.get("id") or uuid.uuid4())
        payload["run_id"] = str(payload.get("run_id") or "UNKNOWN")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
        payload["r_score"] = float(payload.get("r_score", 0.0))
        payload["threshold"] = float(payload.get("threshold", 0.99))
        payload["ok"] = bool(payload.get("ok", False))
        payload["component_scores"] = dict(payload.get("component_scores") or {})
        payload["details"] = dict(payload.get("details") or {})

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        hash_payload = {
            "id": payload["id"],
            "run_id": payload["run_id"],
            "timestamp": payload["timestamp"],
            "r_score": payload["r_score"],
            "component_scores": payload["component_scores"],
            "ok": payload["ok"],
            "threshold": payload["threshold"],
            "details": payload["details"],
        }

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "replay_validations", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, hash_payload, algo=hash_algo)

            conn.execute(
                """
                INSERT OR REPLACE INTO replay_validations
                (id, run_id, timestamp, r_score, component_scores, ok, threshold, details, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["timestamp"],
                    payload["r_score"],
                    json.dumps(payload["component_scores"]),
                    1 if payload["ok"] else 0,
                    payload["threshold"],
                    json.dumps(payload["details"]),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()

        return payload

    def load_replay_validations(self, run_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, run_id, timestamp, r_score, component_scores, ok, threshold, details
                FROM replay_validations
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()

        records: List[Dict[str, Any]] = []
        for row in rows:
            records.append(
                {
                    "id": row[0],
                    "run_id": row[1],
                    "timestamp": row[2],
                    "r_score": float(row[3]) if row[3] is not None else 0.0,
                    "component_scores": json.loads(row[4]) if row[4] else {},
                    "ok": bool(row[5]),
                    "threshold": float(row[6]) if row[6] is not None else 0.99,
                    "details": json.loads(row[7]) if row[7] else {},
                }
            )
        return records

    def save_optimization_event(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(decision)
        payload["decision_id"] = str(payload.get("decision_id") or payload.get("id") or uuid.uuid4())
        payload["id"] = payload["decision_id"]
        payload["run_id"] = str(payload.get("run_id") or "OPT_RUN")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "optimization_events", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, payload, algo=hash_algo)

            conn.execute(
                """
                INSERT OR REPLACE INTO optimization_events
                (id, run_id, timestamp, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["timestamp"],
                    json.dumps(payload),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()
        return payload

    def load_optimization_events(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM optimization_events
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def verify_optimization_chain(self, run_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM optimization_events
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()

        row_dicts = [
            {
                "payload": row[0],
                "prev_hash": row[1],
                "hash": row[2],
                "hash_algo": row[3],
            }
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {
            "ok": ok,
            "checked": len(row_dicts),
            "first_bad_index": first_bad_index,
            "reason": reason,
        }

    def save_reflect_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(decision)
        payload["id"] = str(payload.get("id") or uuid.uuid4())
        payload["run_id"] = str(payload.get("run_id") or "UNKNOWN")
        payload["cycle_id"] = str(payload.get("cycle_id") or "UNKNOWN:0")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
        payload["Fs"] = float(payload.get("Fs", 0.0))
        payload["classification"] = str(payload.get("classification") or "unknown")

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "insight_ledger", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, payload, algo=hash_algo)

            conn.execute(
                """
                INSERT OR REPLACE INTO insight_ledger
                (id, run_id, cycle_id, timestamp, Fs, classification, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["cycle_id"],
                    payload["timestamp"],
                    payload["Fs"],
                    payload["classification"],
                    json.dumps(payload),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()
        return payload

    def load_reflect_decisions(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM insight_ledger
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def verify_reflect_chain(self, run_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM insight_ledger
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()

        row_dicts = [
            {
                "payload": row[0],
                "prev_hash": row[1],
                "hash": row[2],
                "hash_algo": row[3],
            }
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {
            "ok": ok,
            "checked": len(row_dicts),
            "first_bad_index": first_bad_index,
            "reason": reason,
        }

    def save_lambda_history(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        payload["id"] = str(payload.get("id") or uuid.uuid4())
        payload["run_id"] = str(payload.get("run_id") or "GLOBAL")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None

        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "lambda_history", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, payload, algo=hash_algo)
            conn.execute(
                """
                INSERT OR REPLACE INTO lambda_history
                (id, run_id, timestamp, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["timestamp"],
                    json.dumps(payload),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()
        return payload

    def load_lambda_history(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM lambda_history
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def verify_lambda_chain(self, run_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM lambda_history
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        row_dicts = [
            {"payload": row[0], "prev_hash": row[1], "hash": row[2], "hash_algo": row[3]}
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {"ok": ok, "checked": len(row_dicts), "first_bad_index": first_bad_index, "reason": reason}

    def save_bayes_posterior(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        payload["id"] = str(payload.get("id") or uuid.uuid4())
        payload["run_id"] = str(payload.get("run_id") or "GLOBAL")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
        payload["alpha"] = float(payload.get("alpha", 1.0))
        payload["beta"] = float(payload.get("beta", 1.0))
        payload["mean"] = float(payload.get("posterior_mean", payload.get("mean", 0.5)))
        payload["uncertainty"] = float(payload.get("posterior_uncertainty", payload.get("uncertainty", 1.0)))

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None
        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "bayes_posteriors", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, payload, algo=hash_algo)
            conn.execute(
                """
                INSERT OR REPLACE INTO bayes_posteriors
                (id, run_id, timestamp, alpha, beta, mean, uncertainty, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["timestamp"],
                    payload["alpha"],
                    payload["beta"],
                    payload["mean"],
                    payload["uncertainty"],
                    json.dumps(payload),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()
        return payload

    def load_bayes_posteriors(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM bayes_posteriors
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def verify_bayes_chain(self, run_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM bayes_posteriors
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        row_dicts = [
            {"payload": row[0], "prev_hash": row[1], "hash": row[2], "hash_algo": row[3]}
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {"ok": ok, "checked": len(row_dicts), "first_bad_index": first_bad_index, "reason": reason}

    def save_consensus_insight(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        payload["id"] = str(payload.get("id") or uuid.uuid4())
        payload["run_id"] = str(payload.get("run_id") or "UNKNOWN")
        payload["cycle_id"] = str(payload.get("cycle_id") or "UNKNOWN:0")
        payload["timestamp"] = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())
        payload["consensus_Fs"] = float(payload.get("consensus_Fs", 0.0))
        payload["disagreement"] = float(payload.get("disagreement", 0.0))

        mode = self._audit_chain_mode()
        chain_id = derive_chain_id({"run_id": payload["run_id"]}, default="GLOBAL")
        prev_hash: Optional[str] = None
        current_hash: Optional[str] = None
        hash_algo: Optional[str] = None
        with sqlite3.connect(self.db_path) as conn:
            if mode == "log":
                prev_hash = self._last_hash_for_chain(conn, "consensus_insights", chain_id)
                hash_algo = "sha256"
                current_hash = compute_hash(prev_hash, payload, algo=hash_algo)
            conn.execute(
                """
                INSERT OR REPLACE INTO consensus_insights
                (id, run_id, cycle_id, timestamp, consensus_Fs, disagreement, payload, chain_id, prev_hash, hash, hash_algo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["run_id"],
                    payload["cycle_id"],
                    payload["timestamp"],
                    payload["consensus_Fs"],
                    payload["disagreement"],
                    json.dumps(payload),
                    chain_id,
                    prev_hash,
                    current_hash,
                    hash_algo,
                ),
            )
            conn.commit()
        return payload

    def load_consensus_insights(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload
                FROM consensus_insights
                WHERE run_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def verify_consensus_chain(self, run_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM consensus_insights
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
            rows = cursor.fetchall()
        row_dicts = [
            {"payload": row[0], "prev_hash": row[1], "hash": row[2], "hash_algo": row[3]}
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {"ok": ok, "checked": len(row_dicts), "first_bad_index": first_bad_index, "reason": reason}

    def verify_events_chain(self, chain_id: str, limit: int = 500) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM events
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (chain_id, limit),
            )
            rows = cursor.fetchall()

        row_dicts = [
            {
                "payload": row[0],
                "prev_hash": row[1],
                "hash": row[2],
                "hash_algo": row[3],
            }
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {
            "ok": ok,
            "checked": len(row_dicts),
            "first_bad_index": first_bad_index,
            "reason": reason,
        }

    def verify_cycles_chain(self, chain_id: str, limit: int = 200) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT payload, prev_hash, hash, hash_algo
                FROM cycles
                WHERE chain_id=?
                ORDER BY timestamp ASC, rowid ASC
                LIMIT ?
                """,
                (chain_id, limit),
            )
            rows = cursor.fetchall()

        row_dicts = [
            {
                "payload": row[0],
                "prev_hash": row[1],
                "hash": row[2],
                "hash_algo": row[3],
            }
            for row in rows
        ]
        ok, first_bad_index, reason = verify_chain(row_dicts)
        return {
            "ok": ok,
            "checked": len(row_dicts),
            "first_bad_index": first_bad_index,
            "reason": reason,
        }
