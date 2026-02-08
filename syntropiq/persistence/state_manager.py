"""
Persistent State Manager - SQLite storage for governance state

Stores trust scores, suppression state, drift history, and execution results
to enable continuous operation and trust convergence over time.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class PersistentStateManager:
    """
    Manages persistent storage of governance state using SQLite.

    Stores:
    - Agent trust scores and history
    - Suppression state and redemption cycles
    - Drift detection history
    - Execution results
    - Reflections from RIF
    """

    def __init__(self, db_path: str = "governance_state.db"):
        """
        Initialize persistent state manager.

        Args:
            db_path: Path to SQLite database file
        """
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Trust scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trust_scores (
                agent_id TEXT PRIMARY KEY,
                trust_score REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trust history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trust_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                trust_score REAL NOT NULL,
                delta REAL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Suppression state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppression_state (
                agent_id TEXT PRIMARY KEY,
                is_suppressed BOOLEAN NOT NULL,
                redemption_cycle INTEGER DEFAULT 0,
                suppressed_since TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Drift history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                trust_before REAL NOT NULL,
                trust_after REAL NOT NULL,
                drift_delta REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Execution results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                latency REAL,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Reflections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reflection_text TEXT NOT NULL,
                constraint_score INTEGER NOT NULL,
                grounded BOOLEAN,
                recursive BOOLEAN,
                performative_flag BOOLEAN,
                contradiction BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def get_trust_scores(self) -> Dict[str, float]:
        """Get current trust scores for all agents."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT agent_id, trust_score FROM trust_scores")

        return {row['agent_id']: row['trust_score'] for row in cursor.fetchall()}

    def update_trust_scores(self, trust_updates: Dict[str, float], reason: str = None):
        """
        Update trust scores and record history.

        Args:
            trust_updates: Dictionary of {agent_id: new_trust_score}
            reason: Optional reason for update (e.g., "success", "failure")
        """
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()

        for agent_id, new_score in trust_updates.items():
            # Get old score for delta calculation
            cursor.execute("SELECT trust_score FROM trust_scores WHERE agent_id = ?", (agent_id,))
            result = cursor.fetchone()
            old_score = result['trust_score'] if result else 0.0
            delta = new_score - old_score

            # Update or insert trust score
            cursor.execute("""
                INSERT INTO trust_scores (agent_id, trust_score, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    trust_score = excluded.trust_score,
                    updated_at = excluded.updated_at
            """, (agent_id, new_score, timestamp))

            # Record history
            cursor.execute("""
                INSERT INTO trust_history (agent_id, trust_score, delta, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, new_score, delta, reason, timestamp))

        self.conn.commit()

    def get_trust_history(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get trust score history for an agent."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT trust_score, delta, reason, timestamp
            FROM trust_history
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_suppression_state(self) -> Dict[str, Dict]:
        """Get suppression state for all agents."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT agent_id, is_suppressed, redemption_cycle, suppressed_since
            FROM suppression_state
        """)

        return {
            row['agent_id']: {
                'is_suppressed': bool(row['is_suppressed']),
                'redemption_cycle': row['redemption_cycle'],
                'suppressed_since': row['suppressed_since']
            }
            for row in cursor.fetchall()
        }

    def update_suppression_state(self, agent_id: str, is_suppressed: bool, redemption_cycle: int = 0):
        """Update suppression state for an agent."""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO suppression_state (agent_id, is_suppressed, redemption_cycle, suppressed_since, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                is_suppressed = excluded.is_suppressed,
                redemption_cycle = excluded.redemption_cycle,
                suppressed_since = CASE
                    WHEN excluded.is_suppressed = 1 AND is_suppressed = 0 THEN excluded.suppressed_since
                    WHEN excluded.is_suppressed = 0 THEN NULL
                    ELSE suppressed_since
                END,
                updated_at = excluded.updated_at
        """, (agent_id, is_suppressed, redemption_cycle, timestamp if is_suppressed else None, timestamp))

        self.conn.commit()

    def record_drift(self, agent_id: str, trust_before: float, trust_after: float):
        """Record drift detection event."""
        cursor = self.conn.cursor()
        drift_delta = trust_after - trust_before

        cursor.execute("""
            INSERT INTO drift_history (agent_id, trust_before, trust_after, drift_delta)
            VALUES (?, ?, ?, ?)
        """, (agent_id, trust_before, trust_after, drift_delta))

        self.conn.commit()

    def record_execution_results(self, results: List):
        """Record execution results."""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()

        for result in results:
            metadata_json = json.dumps(result.metadata) if hasattr(result, 'metadata') else None

            cursor.execute("""
                INSERT INTO execution_results (task_id, agent_id, success, latency, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (result.task_id, result.agent_id, result.success, result.latency, metadata_json, timestamp))

        self.conn.commit()

    def record_reflection(self, reflection_text: str, result: Dict):
        """Record RIF reflection."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO reflections (
                reflection_text, constraint_score, grounded, recursive,
                performative_flag, contradiction
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            reflection_text,
            result.get('constraint_score', 0),
            result.get('grounded', False),
            result.get('recursive', False),
            result.get('performative_flag', False),
            result.get('contradiction', False)
        ))

        self.conn.commit()

    def get_recent_reflections(self, limit: int = 10) -> List[Dict]:
        """Get recent reflections."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT reflection_text, constraint_score, timestamp
            FROM reflections
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict:
        """Get governance statistics."""
        cursor = self.conn.cursor()

        # Total executions
        cursor.execute("SELECT COUNT(*) as total FROM execution_results")
        total_executions = cursor.fetchone()['total']

        # Success rate
        cursor.execute("SELECT AVG(CAST(success AS FLOAT)) as success_rate FROM execution_results")
        success_rate = cursor.fetchone()['success_rate'] or 0.0

        # Currently suppressed agents
        cursor.execute("SELECT COUNT(*) as suppressed FROM suppression_state WHERE is_suppressed = 1")
        suppressed_count = cursor.fetchone()['suppressed']

        # Total reflections
        cursor.execute("SELECT COUNT(*) as total FROM reflections WHERE constraint_score >= 3")
        valid_reflections = cursor.fetchone()['total']

        return {
            'total_executions': total_executions,
            'success_rate': round(success_rate, 3),
            'suppressed_agents': suppressed_count,
            'valid_reflections': valid_reflections
        }

    def close(self):
        """Close database connection."""
        self.conn.close()