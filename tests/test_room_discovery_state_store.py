from services.room_discovery_state_store import (
    RoomDiscoveryStateStore,
)

from models.room_discovery_models import (
    RoomDiscoveryState,
)


def test_store_roundtrip(
    tmp_path,
):

    state = RoomDiscoveryState()

    state.discover("R001")
    state.discover("R002")

    file_path = (
        tmp_path /
        "room_discovery.json"
    )

    store = RoomDiscoveryStateStore()

    store.save(
        file_path,
        state,
    )

    loaded = store.load(
        file_path
    )

    assert loaded.discovery_order == [
        "R001",
        "R002",
    ]