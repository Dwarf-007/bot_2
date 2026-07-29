
"""
REPOSITORIES/LOCATION_REPOSITORY.PY
Compatibility-hardened location repository.

Refactor 20 notes:
- Adds list_rooms(campaign_id=None) used by health/progress/graph builder.
- Keeps raw_json/source_chunk_ids support for generated room_data.json.
- get_room accepts room_id only for backward compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from repositories.base import BaseRepository


class LocationRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Fixed_Locations (
                    room_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL DEFAULT 'default',
                    title TEXT,
                    room_slug TEXT,
                    facts TEXT NOT NULL DEFAULT '',
                    exits_json TEXT NOT NULL DEFAULT '{}',
                    monsters_json TEXT NOT NULL DEFAULT '[]',
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    source_chunk_ids_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_fixed_locations_campaign
                ON Fixed_Locations(campaign_id)
                """
            )
            conn.commit()

    def upsert_room(self, room: Dict[str, Any]) -> None:
        self.ensure_schema()
        room_id = str(room.get("room_id") or "").strip()
        if not room_id:
            raise ValueError("room_id is required")
        raw = room.get("raw") if isinstance(room.get("raw"), dict) else dict(room)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Fixed_Locations (
                    room_id, campaign_id, title, room_slug, facts,
                    exits_json, monsters_json, raw_json, source_chunk_ids_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(room_id)
                DO UPDATE SET
                    campaign_id = excluded.campaign_id,
                    title = excluded.title,
                    room_slug = excluded.room_slug,
                    facts = excluded.facts,
                    exits_json = excluded.exits_json,
                    monsters_json = excluded.monsters_json,
                    raw_json = excluded.raw_json,
                    source_chunk_ids_json = excluded.source_chunk_ids_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    room_id,
                    str(room.get("campaign_id") or "default"),
                    self._optional_str(room.get("title")),
                    self._optional_str(room.get("room_slug") or room.get("slug")),
                    str(room.get("facts") or ""),
                    self.db.safe_json_dump(room.get("exits", {}) or {}),
                    self.db.safe_json_dump(room.get("monsters", []) or []),
                    self.db.safe_json_dump(raw or {}),
                    self.db.safe_json_dump(room.get("source_chunk_ids", []) or []),
                ),
            )
            conn.commit()

    def get_room(self, room_id: str | None) -> Optional[Dict[str, Any]]:
        self.ensure_schema()
        if not room_id:
            return None
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT room_id, campaign_id, title, room_slug, facts,
                       exits_json, monsters_json, raw_json, source_chunk_ids_json
                FROM Fixed_Locations
                WHERE room_id = ?
                """,
                (str(room_id),),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_rooms(self, campaign_id: str | None = None) -> List[Dict[str, Any]]:
        self.ensure_schema()
        if campaign_id:
            with self.db.get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT room_id, campaign_id, title, room_slug, facts,
                           exits_json, monsters_json, raw_json, source_chunk_ids_json
                    FROM Fixed_Locations
                    WHERE campaign_id = ?
                    ORDER BY room_id
                    """,
                    (str(campaign_id),),
                ).fetchall()
        else:
            with self.db.get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT room_id, campaign_id, title, room_slug, facts,
                           exits_json, monsters_json, raw_json, source_chunk_ids_json
                    FROM Fixed_Locations
                    ORDER BY campaign_id, room_id
                    """
                ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        raw = self.db.safe_json_load(row["raw_json"], {})
        return {
            "room_id": row["room_id"],
            "campaign_id": row["campaign_id"],
            "title": row["title"],
            "room_slug": row["room_slug"],
            "facts": row["facts"] or "",
            "exits": self.db.safe_json_load(row["exits_json"], {}),
            "monsters": self.db.safe_json_load(row["monsters_json"], []),
            "raw": raw,
            "source_chunk_ids": self.db.safe_json_load(row["source_chunk_ids_json"], []),
        }

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
