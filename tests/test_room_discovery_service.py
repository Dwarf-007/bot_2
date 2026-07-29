from models.room_discovery_models import (
    RoomDiscoveryState,
)

from services.room_discovery_service import (
    RoomDiscoveryService,
)


def test_discover_room():

    state = RoomDiscoveryState()

    svc = RoomDiscoveryService()

    assert svc.discover_room(
        state,
        "R001"
    )

    assert svc.discover_room(
        state,
        "R001"
    ) is False

    assert svc.discovered_count(
        state
    ) == 1