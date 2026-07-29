from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class MovementState:
    campaign_id: str
    current_room_id: str
    visited_rooms: List[str] = field(default_factory=list)
    path_history: List[str] = field(default_factory=list)
    flags: Dict[str, Any] = field(default_factory=dict)

    def ensure_current_visited(self) -> None:
        if self.current_room_id and self.current_room_id not in self.visited_rooms:
            self.visited_rooms.append(self.current_room_id)

    def to_dict(self) -> Dict[str, Any]:
        self.ensure_current_visited()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MovementState':
        state = cls(
            campaign_id=str(data.get('campaign_id') or ''),
            current_room_id=str(data.get('current_room_id') or ''),
            visited_rooms=list(data.get('visited_rooms') or []),
            path_history=list(data.get('path_history') or []),
            flags=dict(data.get('flags') or {}),
        )
        state.ensure_current_visited()
        return state

@dataclass
class MovementOption:
    room_id: str
    direction: str
    edge_type: str
    confidence: str
    description: str = ''
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MovementResult:
    ok: bool
    message: str
    state: MovementState
    room: Optional[Dict[str, Any]] = None
    options: List[MovementOption] = field(default_factory=list)
    chosen: Optional[MovementOption] = None
    ambiguity: List[MovementOption] = field(default_factory=list)
    map_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ok': self.ok,
            'message': self.message,
            'state': self.state.to_dict(),
            'room': self.room,
            'options': [x.to_dict() for x in self.options],
            'chosen': self.chosen.to_dict() if self.chosen else None,
            'ambiguity': [x.to_dict() for x in self.ambiguity],
            'map_file': self.map_file,
        }
