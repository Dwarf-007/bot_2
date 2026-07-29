from __future__ import annotations

from models.room_discovery_models import (
    RoomDiscoveryState,
)


class RoomDiscoveryService:

    def discover_room(
        self,
        state: RoomDiscoveryState,
        room_id: str,
    ) -> bool:

        return state.discover(room_id)

    def is_discovered(
        self,
        state: RoomDiscoveryState,
        room_id: str,
    ) -> bool:

        return room_id in state.discovered_rooms

    def get_discovered_rooms(
        self,
        state: RoomDiscoveryState,
    ) -> list:
        return list(
            state.discovery_order
        )

    def discovered_count(
        self,
        state: RoomDiscoveryState,
    ) -> int:

        return len(
            state.discovered_rooms
        )
