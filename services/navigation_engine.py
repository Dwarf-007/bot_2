
"""
SERVICES/NAVIGATION_ENGINE.PY
Deterministic graph navigation.
"""

from __future__ import annotations

from typing import Optional

from core.room_graph_models import MovementResult, RoomGraph


class NavigationEngine:
    def __init__(self, graph: RoomGraph | None = None) -> None:
        self.graph = graph or RoomGraph()

    def set_graph(self, graph: RoomGraph) -> None:
        self.graph = graph

    def try_move(self, current_room_id: str | None, direction: str | None) -> MovementResult:
        if not current_room_id:
            return MovementResult(False, from_room_id=None, direction=direction, reason="no_current_room")
        current = self.graph.get_room(current_room_id)
        if not current:
            return MovementResult(False, from_room_id=current_room_id, direction=direction, reason="current_room_not_found")
        if not direction:
            return MovementResult(False, from_room_id=current_room_id, direction=direction, reason="exit_not_found")
        target = current.exits.get(str(direction).lower()) or current.exits.get(str(direction))
        if not target:
            return MovementResult(False, from_room_id=current_room_id, direction=direction, reason="exit_not_found")
        if not self.graph.get_room(target):
            return MovementResult(False, from_room_id=current_room_id, to_room_id=target, direction=direction, reason="target_room_not_found")
        return MovementResult(True, from_room_id=current_room_id, to_room_id=target, direction=direction, reason="ok")

    def is_adjacent(self, current_room_id: str | None, next_room_id: str | None) -> bool:
        current = self.graph.get_room(current_room_id)
        if not current or not next_room_id:
            return False
        return str(next_room_id) in set(str(value) for value in current.exits.values())

    def direction_to(self, current_room_id: str | None, target_room_id: str | None) -> Optional[str]:
        current = self.graph.get_room(current_room_id)
        if not current or not target_room_id:
            return None
        for direction, room_id in current.exits.items():
            if str(room_id) == str(target_room_id):
                return direction
        return None

    def find_room_by_title_hint(self, hint: str) -> Optional[str]:
        return self.graph.find_room_by_title_hint(hint)
