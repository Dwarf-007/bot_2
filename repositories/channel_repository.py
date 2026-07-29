
"""
REPOSITORIES/CHANNEL_REPOSITORY.PY
Compatibility-hardened channel state repository.

Refactor 20 notes:
- Adds generic update_field(...) used by CampaignService.
- Ensures campaign_id is part of default state.
- Keeps backward-compatible state JSON storage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.channel_state import ChannelState
from repositories.base import BaseRepository


class ChannelRepository(BaseRepository):
    def ensure_schema(self) -> None:
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Channel_State (
                    channel_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get_state(self, channel_id: str) -> ChannelState:
        self.ensure_schema()
        with self.db.get_db_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM Channel_State WHERE channel_id = ?",
                (str(channel_id),),
            ).fetchone()
        if not row:
            state = self.default_state()
            self.save_state(channel_id, state)
            return ChannelState(state)
        state = self.db.safe_json_load(row["state_json"], {})
        return ChannelState(self._merge_defaults(state))

    def save_state(self, channel_id: str, state: Dict[str, Any]) -> None:
        self.ensure_schema()
        merged = self._merge_defaults(state or {})
        with self.db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO Channel_State (channel_id, state_json)
                VALUES (?, ?)
                ON CONFLICT(channel_id)
                DO UPDATE SET state_json = excluded.state_json, updated_at = CURRENT_TIMESTAMP
                """,
                (str(channel_id), self.db.safe_json_dump(merged)),
            )
            conn.commit()

    def update_field(self, channel_id: str, field_name: str, value: Any) -> None:
        state = self.get_state(channel_id)
        state[str(field_name)] = value
        self.save_state(channel_id, state)

    def set_location(self, channel_id: str, room_id: str | None) -> None:
        state = self.get_state(channel_id)
        state["current_location_id"] = room_id
        if room_id:
            visited = list(state.get("visited_rooms", []))
            if room_id not in visited:
                visited.append(room_id)
            state["visited_rooms"] = visited
        self.save_state(channel_id, state)

    def set_mode(self, channel_id: str, mode: str) -> None:
        self.update_field(channel_id, "mode", str(mode or "campaign"))

    def set_style(self, channel_id: str, style: str) -> None:
        self.update_field(channel_id, "style", str(style or "grimdark"))

    def set_difficulty(self, channel_id: str, difficulty: str) -> None:
        self.update_field(channel_id, "difficulty", str(difficulty or "standard"))

    def add_player(self, channel_id: str, player_id: str) -> None:
        state = self.get_state(channel_id)
        players = list(state.get("players", []))
        player_text = str(player_id)
        if player_text not in players:
            players.append(player_text)
        state["players"] = players
        self.save_state(channel_id, state)

    def append_context_message(self, channel_id: str, player_id: str, text: str, limit: int = 10) -> None:
        state = self.get_state(channel_id)
        window = list(state.get("context_window", []))
        window.append({"player_id": str(player_id), "text": str(text or "")})
        state["context_window"] = window[-max(1, int(limit or 10)):]
        self.save_state(channel_id, state)

    def set_active_check(self, channel_id: str, check: str | None, dc: int | None = None) -> None:
        state = self.get_state(channel_id)
        state["active_check"] = check
        state["active_dc"] = dc
        self.save_state(channel_id, state)

    def clear_active_check(self, channel_id: str) -> None:
        state = self.get_state(channel_id)
        state.pop("active_check", None)
        state.pop("active_check_dc", None)
        state.pop("required_check", None)
        state.pop("dc", None)
        self.save_state(channel_id, state)

    def reset_state(self, channel_id: str) -> None:
        """Visszaállítja a csatorna állapotát az alapértelmezett (kiválasztó) állapotra."""
        self.save_state(channel_id, self.default_state())


    @staticmethod
    def default_state() -> Dict[str, Any]:
        return {
            "campaign_id": "default",
            "current_state": "EXPLORATION",
            "current_location_id": None,
            "active_player": None,
            "players": [],
            "party": [],              # jóváhagyott játékosok
            "pending_players": [],    # függő csatlakozási kérelmek
            "visited_rooms": [],
            "inventory_keys": [],
            "context_window": [],
            "active_check": None,
            "active_dc": None,
            "mode": "campaign",
            "style": "grimdark",
            "difficulty": "standard",
        }

    @classmethod
    def _merge_defaults(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        merged = cls.default_state()
        merged.update(state or {})
        if not merged.get("campaign_id"):
            merged["campaign_id"] = "default"
        return merged
