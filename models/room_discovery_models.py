from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RoomDiscoveryState:
    """
    First-class room discovery tracking.

    Independent from:
      - path_history
      - visited_cells
      - visible_cells
    """

    discovered_rooms: set[str] = field(
        default_factory=set
    )

    discovery_order: list[str] = field(
        default_factory=list
    )

    def discover(self, room_id: str) -> bool:

        if not room_id:
            return False

        if room_id in self.discovered_rooms:
            return False

        self.discovered_rooms.add(room_id)
        self.discovery_order.append(room_id)

        return True