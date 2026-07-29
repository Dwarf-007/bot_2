
"""
REPOSITORIES/ROOM_ALIAS_REPOSITORY.PY
Persistence for campaign-scoped room aliases.

Refactor 20 notes:
- Adds count_aliases(campaign_id) for doctor output.
- Empty search query returns first aliases instead of zero, useful for diagnostics.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from models.room_alias import RoomAliasRecord
from repositories.base import BaseRepository


class RoomAliasRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Room_Aliases (
                    campaign_id TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    normalized_alias TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    title TEXT,
                    source TEXT NOT NULL DEFAULT 'manual',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (campaign_id, normalized_alias)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_room_alias_room
                ON Room_Aliases(campaign_id, room_id)
                """
            )
            conn.commit()

    def upsert_alias(self, campaign_id: str, alias: str, room_id: str, title: Optional[str] = None, source: str = "manual") -> None:
        self.ensure_schema()
        normalized = self.normalize_alias(alias)
        if not normalized:
            raise ValueError("alias is required")
        if not str(room_id or "").strip():
            raise ValueError("room_id is required")
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Room_Aliases (campaign_id, alias, normalized_alias, room_id, title, source)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, normalized_alias)
                DO UPDATE SET
                    alias = excluded.alias,
                    room_id = excluded.room_id,
                    title = excluded.title,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(campaign_id or "default"), str(alias), normalized, str(room_id), title, str(source or "manual")),
            )
            conn.commit()

    def import_lookup(self, campaign_id: str, lookup: Dict[str, Any], source: str = "room_lookup.json") -> int:
        self.ensure_schema()
        count = 0
        for alias, payload in (lookup or {}).items():
            if not isinstance(payload, dict):
                continue
            room_id = str(payload.get("room_id") or "").strip()
            title = str(payload.get("title") or alias).strip() or None
            slug = str(payload.get("slug") or "").strip()
            if not room_id:
                continue
            self.upsert_alias(campaign_id, alias, room_id, title=title, source=source)
            if title and title != alias:
                self.upsert_alias(campaign_id, title, room_id, title=title, source=source)
            if slug:
                self.upsert_alias(campaign_id, slug, room_id, title=title, source=source)
            self.upsert_alias(campaign_id, room_id, room_id, title=title, source="room_id")
            count += 1
        return count

    def resolve(self, campaign_id: str, value: str) -> Optional[RoomAliasRecord]:
        self.ensure_schema()
        normalized = self.normalize_alias(value)
        if not normalized:
            return None
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, alias, normalized_alias, room_id, title, source
                FROM Room_Aliases
                WHERE campaign_id = ? AND normalized_alias = ?
                """,
                (str(campaign_id or "default"), normalized),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def search(self, campaign_id: str, query: str, limit: int = 10) -> List[RoomAliasRecord]:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit or 10), 50))
        normalized = self.normalize_alias(query)
        with self.db.get_db_connection() as conn:
            if normalized:
                rows = conn.execute(
                    """
                    SELECT campaign_id, alias, normalized_alias, room_id, title, source
                    FROM Room_Aliases
                    WHERE campaign_id = ? AND normalized_alias LIKE ?
                    ORDER BY LENGTH(normalized_alias), alias
                    LIMIT ?
                    """,
                    (str(campaign_id or "default"), f"%{normalized}%", safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT campaign_id, alias, normalized_alias, room_id, title, source
                    FROM Room_Aliases
                    WHERE campaign_id = ?
                    ORDER BY alias
                    LIMIT ?
                    """,
                    (str(campaign_id or "default"), safe_limit),
                ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count_aliases(self, campaign_id: str) -> int:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count_value FROM Room_Aliases WHERE campaign_id = ?",
                (str(campaign_id or "default"),),
            ).fetchone()
        return int(row["count_value"] if row else 0)

    def list_aliases_for_room(self, campaign_id: str, room_id: str) -> List[RoomAliasRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, alias, normalized_alias, room_id, title, source
                FROM Room_Aliases
                WHERE campaign_id = ? AND room_id = ?
                ORDER BY alias
                """,
                (str(campaign_id or "default"), str(room_id)),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def normalize_alias(value: str) -> str:
        text = str(value or "").strip().lower()
        replacements = {"û": "u", "ű": "u", "ú": "u", "ő": "o", "ó": "o", "ö": "o", "á": "a", "é": "e", "í": "i", "ü": "u"}
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[^0-9a-zA-Z]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _row_to_record(row) -> RoomAliasRecord:
        return RoomAliasRecord(
            campaign_id=str(row["campaign_id"]),
            alias=str(row["alias"]),
            normalized_alias=str(row["normalized_alias"]),
            room_id=str(row["room_id"]),
            title=row["title"],
            source=str(row["source"]),
        )
