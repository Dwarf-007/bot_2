
"""
SERVICES/ROOM_GRAPH_BUILDER.PY
Campaign-aware room graph builder.
"""

from __future__ import annotations

from core.room_graph_models import RoomGraph


class RoomGraphBuilder:
    def build_from_location_repository(self, location_repo, campaign_id: str | None = None) -> RoomGraph:
        graph = RoomGraph()
        try:
            rooms = location_repo.list_rooms(campaign_id=campaign_id) if campaign_id else location_repo.list_rooms()
        except TypeError:
            rooms = location_repo.list_rooms()

        for room in rooms:
            room_id = room.get("room_id")
            if not room_id:
                continue
            graph.add_room(
                room_id=room_id,
                title=room.get("title") or room_id,
                exits=room.get("exits", {}) or {},
            )
        return graph
