"""
SERVICES/MEMORY_EVENT_SERVICE.PY
Application service for persistent event-sourced campaign memory.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.game_events import GameEvent, EventTypes
from models.memory_event import MemoryEventRecord


class MemoryEventService:
    DEFAULT_PERSISTED_EVENT_TYPES = {
        EventTypes.PLAYER_MOVED,
        EventTypes.ROOM_ENTERED,
        EventTypes.TRAP_TRIGGERED,
        EventTypes.REQUIRED_CHECK,
        EventTypes.DAMAGE,
        EventTypes.PLAYER_ROLL,
        EventTypes.COMBAT_START,
        EventTypes.COMBAT_END,
        EventTypes.ALL_MONSTERS_DEFEATED,
        EventTypes.REST_REQUESTED,
        EventTypes.REST_COMPLETED,
        EventTypes.REST_INTERRUPTED,
        EventTypes.XP_GAINED,
        EventTypes.INVENTORY_UPDATED,
        EventTypes.ITEM_GAINED,
        EventTypes.NPC_INTERACTION,
    }

    def __init__(self, memory_repo, persisted_event_types: Iterable[str] | None = None) -> None:
        self.memory_repo = memory_repo
        self.persisted_event_types = set(persisted_event_types or self.DEFAULT_PERSISTED_EVENT_TYPES)
        self.memory_repo.ensure_schema()

    def handle_event(self, event: GameEvent) -> None:
        if event.type not in self.persisted_event_types:
            return
        channel_id = self._extract_channel_id(event)
        if not channel_id:
            return
        self.memory_repo.add_event(channel_id=channel_id, event_type=event.type, data=event.payload or {})

    def add_manual_memory(self, channel_id: str, event_type: str, data: Dict[str, Any]) -> int:
        return self.memory_repo.add_event(channel_id=channel_id, event_type=event_type, data=data)

    def recent(self, channel_id: str, limit: int = 20) -> List[MemoryEventRecord]:
        return self.memory_repo.list_recent_events(channel_id, limit=limit)

    @staticmethod
    def _extract_channel_id(event: GameEvent) -> str | None:
        payload = event.payload or {}
        value = payload.get("channel_id")
        if value is None:
            return None
        text = str(value).strip()
        return text or None
