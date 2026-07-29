"""
REPOSITORIES/COMBAT_REPOSITORY.PY
Persistence abstraction for active combat lifecycle tracking.

Important boundary:
- HP, initiative, conditions and combat rolls are handled by Avrae.
- This repository tracks only minimal lifecycle metadata so the AI DM can react
  when all known monsters are defeated.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from models.combat_feedback import CombatMonsterEntry, CombatStateSnapshot
from repositories.base import BaseRepository


class CombatRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Combat_States (
                    channel_id TEXT PRIMARY KEY,
                    active INTEGER NOT NULL,
                    room_id TEXT,
                    monsters_json TEXT NOT NULL,
                    xp_reward_total INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def start_combat(
        self,
        channel_id: str,
        room_id: Optional[str],
        monsters: List[Dict[str, Any]],
        xp_reward_total: int = 0,
    ) -> None:
        self.ensure_schema()
        normalized = self._normalize_monsters(monsters)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Combat_States (
                    channel_id, active, room_id, monsters_json, xp_reward_total
                )
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(channel_id)
                DO UPDATE SET
                    active = excluded.active,
                    room_id = excluded.room_id,
                    monsters_json = excluded.monsters_json,
                    xp_reward_total = excluded.xp_reward_total,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(channel_id),
                    room_id,
                    json.dumps(normalized, ensure_ascii=False),
                    int(xp_reward_total or 0),
                ),
            )
            conn.commit()

    def get_combat_state(self, channel_id: str) -> CombatStateSnapshot:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT active, room_id, monsters_json, xp_reward_total
                FROM Combat_States
                WHERE channel_id = ?
                """,
                (str(channel_id),),
            ).fetchone()

        if not row:
            return CombatStateSnapshot(channel_id=str(channel_id), active=False, room_id=None)

        try:
            monsters_raw = json.loads(row["monsters_json"] or "[]")
        except json.JSONDecodeError:
            monsters_raw = []

        monsters = [
            CombatMonsterEntry(
                name=str(item.get("name", "")),
                remaining=max(0, int(item.get("remaining", 0))),
            )
            for item in monsters_raw
            if str(item.get("name", "")).strip()
        ]

        return CombatStateSnapshot(
            channel_id=str(channel_id),
            active=bool(row["active"]),
            room_id=row["room_id"],
            monsters=monsters,
            xp_reward_total=int(row["xp_reward_total"] or 0),
        )

    def register_defeated_monster(self, channel_id: str, monster_name: str) -> bool:
        snapshot = self.get_combat_state(channel_id)
        if not snapshot.active:
            return False

        target = self._normalize_name(monster_name)
        updated: List[Dict[str, Any]] = []
        matched = False

        for monster in snapshot.monsters:
            remaining = monster.remaining
            if not matched and remaining > 0 and self._names_match(monster.name, target):
                remaining -= 1
                matched = True
            updated.append({"name": monster.name, "remaining": remaining})

        if not matched:
            return False

        still_active = any(item["remaining"] > 0 for item in updated)
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                UPDATE Combat_States
                SET active = ?, monsters_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ?
                """,
                (1 if still_active else 0, json.dumps(updated, ensure_ascii=False), str(channel_id)),
            )
            conn.commit()
        return True

    def clear_combat(self, channel_id: str) -> None:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            conn.execute("DELETE FROM Combat_States WHERE channel_id = ?", (str(channel_id),))
            conn.commit()

    @staticmethod
    def _normalize_monsters(monsters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        aggregated: Dict[str, int] = {}
        for item in monsters or []:
            name = str(item.get("name") or item.get("monster_name") or "").strip()
            if not name:
                continue
            try:
                count = int(item.get("count", 1))
            except (TypeError, ValueError):
                count = 1
            if count <= 0:
                continue
            aggregated[name] = aggregated.get(name, 0) + count
        return [{"name": name, "remaining": count} for name, count in aggregated.items()]

    @classmethod
    def _names_match(cls, tracked_name: str, defeated_normalized: str) -> bool:
        tracked = cls._normalize_name(tracked_name)
        if tracked == defeated_normalized:
            return True
        return tracked in defeated_normalized or defeated_normalized in tracked

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join(str(value or "").lower().replace("*", "").split())
