from __future__ import annotations

import json
from pathlib import Path

from models.room_discovery_models import (
    RoomDiscoveryState,
)


class RoomDiscoveryStateStore:

    def load(
        self,
        path: str | Path,
    ) -> RoomDiscoveryState:

        file_path = Path(path)

        if not file_path.exists():
            return RoomDiscoveryState()

        data = json.loads(
            file_path.read_text(
                encoding="utf-8"
            )
        )

        state = RoomDiscoveryState()

        state.discovered_rooms = set(
            data.get(
                "discovered_rooms",
                [],
            )
        )

        state.discovery_order = list(
            data.get(
                "discovery_order",
                [],
            )
        )

        return state

    def save(
        self,
        path: str | Path,
        state: RoomDiscoveryState,
    ) -> None:

        Path(path).write_text(
            json.dumps(
                {
                    "discovered_rooms": sorted(
                        state.discovered_rooms
                    ),
                    "discovery_order":
                        state.discovery_order,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )