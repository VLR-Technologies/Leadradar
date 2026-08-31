import sqlite3
import threading
from contextlib import closing
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path


class CallLogStore:
    """Durable SQLite store for lead call decisions."""

    def __init__(
        self,
        db_path: Path,
        *,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.db_path = db_path
        self._now_fn = now_fn
        self._lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS call_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_key TEXT NOT NULL,
                    business_name TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    decision TEXT NOT NULL CHECK (decision IN ('yes', 'no')),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_decisions_created_at "
                "ON call_decisions (created_at)"
            )

    def record(
        self,
        *,
        lead_key: str,
        business_name: str,
        phone: str,
        decision: str,
    ) -> None:
        if decision not in {"yes", "no"}:
            raise ValueError("decision must be 'yes' or 'no'")
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO call_decisions "
                "(lead_key, business_name, phone, decision, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    lead_key,
                    business_name,
                    phone,
                    decision,
                    self._now_fn().isoformat(),
                ),
            )

    def summary(self) -> dict[str, int]:
        today = self._now_fn().date().isoformat()
        with self._lock, closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(decision = 'yes') AS yes_count,
                    SUM(decision = 'no') AS no_count,
                    SUM(substr(created_at, 1, 10) = ?) AS today_count
                FROM call_decisions
                """,
                (today,),
            ).fetchone()
        return {
            "total": row["total"] or 0,
            "yes": row["yes_count"] or 0,
            "no": row["no_count"] or 0,
            "today": row["today_count"] or 0,
        }

    def recent(self, *, limit: int = 200) -> list[dict[str, str]]:
        with self._lock, closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT lead_key, business_name, phone, decision, created_at "
                "FROM call_decisions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def purge_older_than(self, days: int) -> int:
        cutoff = (self._now_fn() - timedelta(days=days)).isoformat()
        with self._lock, closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM call_decisions WHERE created_at < ?",
                (cutoff,),
            )
            return cursor.rowcount