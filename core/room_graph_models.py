
"""
CORE/ROOM_GRAPH_MODELS.PY
Small deterministic room graph models used by navigation/movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class MovementIntent:
    requested: bool
    direction: Optional[str] = None
    target_room_hint: Optional[str] = None
    raw_text: str = ""


@dataclass(frozen=True)
class MovementResult:
    success: bool
    from_room_id: Optional[str] = None
    to_room_id: Optional[str] = None
    direction: Optional[str] = None
    reason: str = ""


@dataclass
class RoomNode:
    room_id: str
    title: str
    exits: Dict[str, str] = field(default_factory=dict)


class RoomGraph:
    def __init__(self) -> None:
        self.rooms: Dict[str, RoomNode] = {}

    def add_room(self, room_id: str, title: str, exits: Dict[str, str] | None = None) -> None:
        self.rooms[str(room_id)] = RoomNode(room_id=str(room_id), title=str(title or room_id), exits=dict(exits or {}))

    def get_room(self, room_id: str | None) -> Optional[RoomNode]:
        if not room_id:
            return None
        return self.rooms.get(str(room_id))

    def find_room_by_title_hint(self, hint: str) -> Optional[str]:
        normalized_hint = str(hint or "").strip().lower()
        if not normalized_hint:
            return None
        if normalized_hint in self.rooms:
            return normalized_hint
        for room_id, room in self.rooms.items():
            if normalized_hint == room.title.lower() or normalized_hint in room.title.lower():
                return room_id
        return None
