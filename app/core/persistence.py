"""
SQLite Persistence Layer for NomadOS.
Zero-config, file-based persistence that replaces in-memory Dict storage.
Stores trips, users, and audit logs with JSON serialization.

In production, this can be swapped for PostgreSQL/Redis with the same interface.
"""
import json
import sqlite3
import os
import time
import threading
from typing import Dict, Any, Optional, List
from app.core.logging import logger


def _resolve_db_path() -> str:
    if os.environ.get("NOMADOS_DB_PATH"):
        return os.environ["NOMADOS_DB_PATH"]
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/nomados.db"
    return os.path.join(os.path.dirname(__file__), "..", "..", "nomados.db")

DB_PATH = _resolve_db_path()



class PersistenceLayer:
    """
    Thread-safe SQLite persistence for NomadOS.
    Stores canonical trips, user profiles, and an audit log.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = os.path.abspath(db_path)
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _init_schema(self):
        """Creates tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'planning',
                data TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                profile TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT,
                user_id TEXT DEFAULT 'system',
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                timestamp REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
            CREATE INDEX IF NOT EXISTS idx_audit_trip ON audit_log(trip_id);
            CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp);
        """)
        conn.commit()
        logger.info(f"SQLite persistence initialized at {self.db_path}")

    # ============================================================
    # Trip CRUD
    # ============================================================

    def save_trip(self, trip_id: str, trip_data: Dict[str, Any]) -> None:
        """Saves or updates a trip."""
        conn = self._get_conn()
        now = time.time()
        title = trip_data.get("title", "Untitled Trip")
        status = trip_data.get("status", "planning")
        data_json = json.dumps(trip_data, default=str)

        conn.execute("""
            INSERT INTO trips (trip_id, title, status, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(trip_id) DO UPDATE SET
                title = excluded.title,
                status = excluded.status,
                data = excluded.data,
                updated_at = excluded.updated_at
        """, (trip_id, title, status, data_json, now, now))
        conn.commit()

        self._audit("save_trip", trip_id, f"Saved trip: {title}")

    def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a trip by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM trips WHERE trip_id = ?", (trip_id,)
        ).fetchone()
        if row:
            return json.loads(row["data"])
        return None

    def list_trips(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists trips, optionally filtered by status."""
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT data FROM trips WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT data FROM trips ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row["data"]) for row in rows]

    def delete_trip(self, trip_id: str) -> bool:
        """Deletes a trip."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM trips WHERE trip_id = ?", (trip_id,))
        conn.commit()
        if cursor.rowcount > 0:
            self._audit("delete_trip", trip_id, "Trip deleted")
            return True
        return False

    # ============================================================
    # User CRUD
    # ============================================================

    def save_user(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Saves or updates a user profile."""
        conn = self._get_conn()
        name = profile.get("name", "Unknown")
        profile_json = json.dumps(profile, default=str)
        now = time.time()

        conn.execute("""
            INSERT INTO users (user_id, name, profile, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                profile = excluded.profile
        """, (user_id, name, profile_json, now))
        conn.commit()

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user profile."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT profile FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return json.loads(row["profile"])
        return None

    # ============================================================
    # Audit Log
    # ============================================================

    def _audit(self, action: str, trip_id: str = "", details: str = "", user_id: str = "system"):
        """Records an audit log entry."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO audit_log (trip_id, user_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                (trip_id, user_id, action, details, time.time())
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"Audit log write failed (non-critical): {e}")

    def get_audit_log(self, trip_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Retrieves audit log entries."""
        conn = self._get_conn()
        if trip_id:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE trip_id = ? ORDER BY timestamp DESC LIMIT ?",
                (trip_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    # ============================================================
    # Stats
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Returns persistence statistics."""
        conn = self._get_conn()
        trip_count = conn.execute("SELECT COUNT(*) as c FROM trips").fetchone()["c"]
        user_count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        audit_count = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]
        db_size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            "total_trips": trip_count,
            "total_users": user_count,
            "total_audit_entries": audit_count,
            "db_size_kb": round(db_size_bytes / 1024, 1),
            "db_path": self.db_path
        }


# Global singleton
persistence = PersistenceLayer()
