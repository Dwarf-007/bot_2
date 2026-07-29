"""
REPOSITORIES/PARTY_REPOSITORY.PY
Party membership persistence per Discord channel.
"""

from __future__ import annotations

from typing import List

from repositories.base import BaseRepository


class PartyRepository(BaseRepository):
    def add_player(self, channel_id: str, player_id: str) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO Party_Members (channel_id, player_id)
                VALUES (?, ?)
                """,
                (str(channel_id), str(player_id)),
            )
            conn.commit()

    def remove_player(self, channel_id: str, player_id: str) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                "DELETE FROM Party_Members WHERE channel_id = ? AND player_id = ?",
                (str(channel_id), str(player_id)),
            )
            conn.commit()

    def get_party_members(self, channel_id: str) -> List[str]:
        with self.db.get_db_connection() as conn:
            rows = conn.execute(
                "SELECT player_id FROM Party_Members WHERE channel_id = ? ORDER BY joined_at, player_id",
                (str(channel_id),),
            ).fetchall()
        return [str(row["player_id"]) for row in rows]
