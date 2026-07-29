
"""
REPOSITORIES/CAMPAIGN_PROGRESS_REPOSITORY.PY
Persistence for campaign scenes, channel progress, and objectives.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.campaign_progress import CampaignObjectiveRecord, CampaignSceneRecord, ChannelProgressRecord
from repositories.base import BaseRepository


class CampaignProgressRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Campaign_Scenes (
                    campaign_id TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    order_index INTEGER NOT NULL DEFAULT 0,
                    room_id TEXT,
                    source TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (campaign_id, scene_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_campaign_scenes_order
                ON Campaign_Scenes(campaign_id, order_index)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Channel_Progress (
                    channel_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    current_scene_id TEXT,
                    current_room_id TEXT,
                    milestone TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Campaign_Objectives (
                    objective_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    scene_id TEXT,
                    room_id TEXT,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_campaign_objectives_channel_status
                ON Campaign_Objectives(channel_id, status)
                """
            )
            conn.commit()

    def upsert_scene(self, scene: Dict[str, Any]) -> None:
        self.ensure_schema()
        campaign_id = str(scene.get("campaign_id") or "default")
        scene_id = str(scene.get("scene_id") or scene.get("id") or "").strip()
        if not scene_id:
            raise ValueError("scene_id is required")
        title = str(scene.get("title") or scene_id)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Campaign_Scenes (
                    campaign_id, scene_id, title, order_index, room_id, source, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(campaign_id, scene_id)
                DO UPDATE SET
                    title = excluded.title,
                    order_index = excluded.order_index,
                    room_id = excluded.room_id,
                    source = excluded.source,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    campaign_id,
                    scene_id,
                    title,
                    int(scene.get("order_index", 0) or 0),
                    self._optional_str(scene.get("room_id")),
                    self._optional_str(scene.get("source")),
                    self.db.safe_json_dump(scene.get("metadata", {}) or {}),
                ),
            )
            conn.commit()

    def list_scenes(self, campaign_id: str) -> List[CampaignSceneRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT campaign_id, scene_id, title, order_index, room_id, source, metadata_json
                FROM Campaign_Scenes
                WHERE campaign_id = ?
                ORDER BY order_index, scene_id
                """,
                (str(campaign_id),),
            ).fetchall()
        return [self._scene_row(row) for row in rows]

    def get_scene(self, campaign_id: str, scene_id: str) -> Optional[CampaignSceneRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT campaign_id, scene_id, title, order_index, room_id, source, metadata_json
                FROM Campaign_Scenes
                WHERE campaign_id = ? AND scene_id = ?
                """,
                (str(campaign_id), str(scene_id)),
            ).fetchone()
        return self._scene_row(row) if row else None

    def set_channel_progress(
        self,
        channel_id: str,
        campaign_id: str,
        current_scene_id: Optional[str] = None,
        current_room_id: Optional[str] = None,
        milestone: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Channel_Progress (
                    channel_id, campaign_id, current_scene_id, current_room_id, milestone, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id)
                DO UPDATE SET
                    campaign_id = excluded.campaign_id,
                    current_scene_id = excluded.current_scene_id,
                    current_room_id = excluded.current_room_id,
                    milestone = excluded.milestone,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(channel_id),
                    str(campaign_id),
                    self._optional_str(current_scene_id),
                    self._optional_str(current_room_id),
                    str(milestone or ""),
                    self.db.safe_json_dump(metadata or {}),
                ),
            )
            conn.commit()

    def get_channel_progress(self, channel_id: str) -> Optional[ChannelProgressRecord]:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, campaign_id, current_scene_id, current_room_id, milestone, metadata_json
                FROM Channel_Progress
                WHERE channel_id = ?
                """,
                (str(channel_id),),
            ).fetchone()
        return self._progress_row(row) if row else None

    def add_objective(
        self,
        channel_id: str,
        campaign_id: str,
        text: str,
        scene_id: Optional[str] = None,
        room_id: Optional[str] = None,
    ) -> int:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO Campaign_Objectives (channel_id, campaign_id, scene_id, room_id, text, status)
                VALUES (?, ?, ?, ?, ?, 'OPEN')
                """,
                (str(channel_id), str(campaign_id), self._optional_str(scene_id), self._optional_str(room_id), str(text)),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def set_objective_status(self, objective_id: int, status: str) -> None:
        self.ensure_schema()
        normalized = str(status or "OPEN").upper()
        completed_sql = "CURRENT_TIMESTAMP" if normalized in {"DONE", "CANCELLED"} else "NULL"
        with self.db.get_db_connection() as conn:
            conn.execute(
                f"""
                UPDATE Campaign_Objectives
                SET status = ?, completed_at = {completed_sql}
                WHERE objective_id = ?
                """,
                (normalized, int(objective_id)),
            )
            conn.commit()

    def list_objectives(self, channel_id: str, include_done: bool = False, limit: int = 50) -> List[CampaignObjectiveRecord]:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit or 50), 200))
        where = "channel_id = ?" if include_done else "channel_id = ? AND status = 'OPEN'"
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT objective_id, channel_id, campaign_id, scene_id, room_id, text, status, created_at, completed_at
                FROM Campaign_Objectives
                WHERE {where}
                ORDER BY objective_id DESC
                LIMIT ?
                """,
                (str(channel_id), safe_limit),
            ).fetchall()
        records = [self._objective_row(row) for row in rows]
        records.reverse()
        return records

    def _scene_row(self, row) -> CampaignSceneRecord:
        return CampaignSceneRecord(
            campaign_id=str(row["campaign_id"]),
            scene_id=str(row["scene_id"]),
            title=str(row["title"]),
            order_index=int(row["order_index"] or 0),
            room_id=self._optional_str(row["room_id"]),
            source=self._optional_str(row["source"]),
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
        )

    def _progress_row(self, row) -> ChannelProgressRecord:
        return ChannelProgressRecord(
            channel_id=str(row["channel_id"]),
            campaign_id=str(row["campaign_id"]),
            current_scene_id=self._optional_str(row["current_scene_id"]),
            current_room_id=self._optional_str(row["current_room_id"]),
            milestone=str(row["milestone"] or ""),
            metadata=self.db.safe_json_load(row["metadata_json"], {}),
        )

    @staticmethod
    def _objective_row(row) -> CampaignObjectiveRecord:
        return CampaignObjectiveRecord(
            objective_id=int(row["objective_id"]),
            channel_id=str(row["channel_id"]),
            campaign_id=str(row["campaign_id"]),
            scene_id=row["scene_id"],
            room_id=row["room_id"],
            text=str(row["text"]),
            status=str(row["status"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
