"""
MODELS/GENERATED_DUNGEON.PY

Source-agnostic data model for procedurally generated dungeons.
Sprint 1 scope: represent a generated dungeon after importing Donjon JSON.

This model deliberately does NOT depend on repositories or runtime services.
Sprint 2 will convert this model into the existing campaign bundle files:
room_data.json, room_lookup.json, rag_index.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


GridPoint = Tuple[int, int]


@dataclass(frozen=True)
class GeneratedDoor:
    door_id: str
    x: int
    y: int
    kind: str = "door"  # door | arch | portcullis | secret | stair_up | stair_down | connector
    locked: bool = False
    trapped: bool = False
    secret: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedTrap:
    trap_id: str
    x: int
    y: int
    kind: str = "trap"
    dc_find: Optional[int] = None
    dc_disable: Optional[int] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedConnection:
    from_room_id: str
    to_room_id: str
    direction: Optional[str] = None
    via: str = "corridor"  # door | corridor | arch | portcullis | secret | inferred
    door_ids: List[str] = field(default_factory=list)
    distance: int = 0
    locked: bool = False
    trapped: bool = False
    secret: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalized_key(self) -> tuple[str, str, Optional[str], str]:
        a, b = sorted([self.from_room_id, self.to_room_id])
        return a, b, self.direction, self.via

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedRoom:
    room_id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    cells: List[GridPoint] = field(default_factory=list)
    exits: Dict[str, str] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    monsters: List[Dict[str, Any]] = field(default_factory=list)
    traps: List[GeneratedTrap] = field(default_factory=list)
    treasures: List[Dict[str, Any]] = field(default_factory=list)
    is_entrance: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["traps"] = [trap.to_dict() for trap in self.traps]
        return data


@dataclass(frozen=True)
class GeneratedDungeon:
    dungeon_id: str
    title: str
    source: str = "unknown"
    width: int = 0
    height: int = 0
    rooms: List[GeneratedRoom] = field(default_factory=list)
    connections: List[GeneratedConnection] = field(default_factory=list)
    doors: List[GeneratedDoor] = field(default_factory=list)
    traps: List[GeneratedTrap] = field(default_factory=list)
    entrance: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_room(self, room_id: str) -> Optional[GeneratedRoom]:
        rid = str(room_id)
        return next((room for room in self.rooms if room.room_id == rid), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dungeon_id": self.dungeon_id,
            "title": self.title,
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "rooms": [room.to_dict() for room in self.rooms],
            "connections": [connection.to_dict() for connection in self.connections],
            "doors": [door.to_dict() for door in self.doors],
            "traps": [trap.to_dict() for trap in self.traps],
            "entrance": self.entrance,
            "metadata": self.metadata,
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "dungeon_id": self.dungeon_id,
            "title": self.title,
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "room_count": len(self.rooms),
            "connection_count": len(self.connections),
            "door_count": len(self.doors),
            "trap_count": len(self.traps),
        }
