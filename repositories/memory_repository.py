"""
REPOSITORIES/MEMORY_REPOSITORY.PY
Persistence abstraction for long-term campaign memory events.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.memory_event import MemoryEventRecord
from repositories.base import BaseRepository


class MemoryRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Memory_Events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_events_channel_created
                ON Memory_Events(channel_id, created_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_events_channel_type
                ON Memory_Events(channel_id, event_type)
                """
            )
            conn.commit()

    def add_event(self, channel_id: str, event_type: str, data: Dict[str, Any] | None = None) -> int:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO Memory_Events (channel_id, event_type, data_json)
                VALUES (?, ?, ?)
                """,
                (str(channel_id), str(event_type), self.db.safe_json_dump(data or {})),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_recent_events(self, channel_id: str, limit: int = 50) -> List[MemoryEventRecord]:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit or 50), 500))
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, event_type, data_json, created_at
                FROM Memory_Events
                WHERE channel_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(channel_id), safe_limit),
            ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        records.reverse()
        return records

    def list_events_by_type(self, channel_id: str, event_type: str, limit: int = 50) -> List[MemoryEventRecord]:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit or 50), 500))
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, event_type, data_json, created_at
                FROM Memory_Events
                WHERE channel_id = ? AND event_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(channel_id), str(event_type), safe_limit),
            ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        records.reverse()
        return records

    def clear_channel_memory(self, channel_id: str) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute("DELETE FROM Memory_Events WHERE channel_id = ?", (str(channel_id),))
            conn.commit()

    def _row_to_record(self, row) -> MemoryEventRecord:
        return MemoryEventRecord(
            id=int(row["id"]),
            channel_id=str(row["channel_id"]),
            event_type=str(row["event_type"]),
            data=self.db.safe_json_load(row["data_json"], {}),
            created_at=row["created_at"],
        )
