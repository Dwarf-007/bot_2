
from services.runtime_visibility_state_service import RuntimeVisibilityStateService


def visibility_state_payload():
    return {
        "campaign_id": "c1",
        "current": {
            "node_id": "s1",
            "node_type": "segment",
            "level": 1,
            "room_id": None,
            "segment_id": "s1",
            "cell": [3, 4],
        },
        "visited_rooms": [],
        "visited_segments": ["s1"],
        "visible_cells": [[3, 4], [3, 5]],
        "explored_cells": [[3, 4]],
        "visited_cells": [[3, 4]],
        "path_history": [],
    }


def test_state_from_raw_accepts_visibility_state_key():
    state = RuntimeVisibilityStateService().state_from_raw({"ok": True, "visibility_state": visibility_state_payload()})
    assert state is not None
    assert state.campaign_id == "c1"
    assert set(state.visible_cells) == {(3, 4), (3, 5)}
    assert state.current.segment_id == "s1"


def test_state_from_raw_still_accepts_state_key():
    state = RuntimeVisibilityStateService().state_from_raw({"ok": True, "state": visibility_state_payload()})
    assert state is not None
    assert set(state.visible_cells) == {(3, 4), (3, 5)}


def test_state_from_raw_returns_none_without_supported_key():
    assert RuntimeVisibilityStateService().state_from_raw({"ok": True, "look": {}}) is None
