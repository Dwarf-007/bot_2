"""
REPOSITORIES/PLAYER_REPOSITORY.PY
Player XP and level persistence.
"""

from __future__ import annotations

from typing import Dict

from repositories.base import BaseRepository


class PlayerRepository(BaseRepository):
    def get_xp(self, channel_id: str, player_id: str) -> Dict[str, int]:
        self._ensure_player_row(channel_id, player_id)
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT current_xp, current_level
                FROM Character_Levels
                WHERE channel_id = ? AND player_id = ?
                """,
                (str(channel_id), str(player_id)),
            ).fetchone()
        if not row:
            return {"current_xp": 0, "current_level": 1}
        return {
            "current_xp": int(row["current_xp"] or 0),
            "current_level": int(row["current_level"] or 1),
        }

    def add_xp(self, channel_id: str, player_id: str, xp: int) -> None:
        safe_xp = max(0, int(xp or 0))
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Character_Levels (channel_id, player_id, current_xp, current_level)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(channel_id, player_id)
                DO UPDATE SET
                    current_xp = current_xp + excluded.current_xp,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(channel_id), str(player_id), safe_xp),
            )
            conn.commit()

    def update_level(self, channel_id: str, player_id: str, new_level: int) -> None:
        level = max(1, int(new_level or 1))
        self._ensure_player_row(channel_id, player_id)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                UPDATE Character_Levels
                SET current_level = ?, updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ? AND player_id = ?
                """,
                (level, str(channel_id), str(player_id)),
            )
            conn.commit()

    def _ensure_player_row(self, channel_id: str, player_id: str) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO Character_Levels (channel_id, player_id, current_xp, current_level)
                VALUES (?, ?, 0, 1)
                """,
                (str(channel_id), str(player_id)),
            )
            conn.commit()
