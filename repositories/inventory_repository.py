"""
REPOSITORIES/INVENTORY_REPOSITORY.PY
Player inventory persistence.
"""

from __future__ import annotations

from typing import Any, Dict

from repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    def get_inventory(self, channel_id: str, player_id: str) -> Dict[str, Any]:
        self._ensure_inventory_row(channel_id, player_id)
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT gold, items_json, ammo_json
                FROM Inventory
                WHERE channel_id = ? AND player_id = ?
                """,
                (str(channel_id), str(player_id)),
            ).fetchone()

        if not row:
            return {"gold": 0.0, "items": {}, "ammo": {}}
        return {
            "gold": float(row["gold"] or 0.0),
            "items": self.db.safe_json_load(row["items_json"], {}),
            "ammo": self.db.safe_json_load(row["ammo_json"], {}),
        }

    def save_inventory(self, channel_id: str, player_id: str, data: Dict[str, Any]) -> None:
        gold = float(data.get("gold", 0.0))
        items = data.get("items", {}) or {}
        ammo = data.get("ammo", {}) or {}
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Inventory (channel_id, player_id, gold, items_json, ammo_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel_id, player_id)
                DO UPDATE SET
                    gold = excluded.gold,
                    items_json = excluded.items_json,
                    ammo_json = excluded.ammo_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(channel_id),
                    str(player_id),
                    gold,
                    self.db.safe_json_dump(items),
                    self.db.safe_json_dump(ammo),
                ),
            )
            conn.commit()

    def _ensure_inventory_row(self, channel_id: str, player_id: str) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO Inventory (channel_id, player_id, gold, items_json, ammo_json)
                VALUES (?, ?, 0, '{}', '{}')
                """,
                (str(channel_id), str(player_id)),
            )
            conn.commit()
