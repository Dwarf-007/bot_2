"""
TEST_CHANNEL_STATE.PY
Validates the typed, backward-compatible ChannelState model and its wiring into
ChannelRepository.get_state.
"""

from __future__ import annotations

from core.channel_state import ChannelState
from persistence import database as db
from repositories.channel_repository import ChannelRepository


def test_channel_state_dict_compatibility() -> None:
    state = ChannelState({"current_location_id": "room_1", "players": ["a", "b"]})
    # Raw dict access still works (backward compatibility).
    assert state["current_location_id"] == "room_1"
    assert state.get("players") == ["a", "b"]
    # Typed attribute access returns the same values.
    assert state.current_location_id == "room_1"
    assert state.players == ["a", "b"]


def test_channel_state_defaults_and_setters() -> None:
    state = ChannelState()
    assert state.campaign_id == "default"
    state.current_location_id = "room_2"
    # Setter writes through to the underlying dict.
    assert state["current_location_id"] == "room_2"
    assert state.current_location_id == "room_2"
    state.players = ["p1"]
    assert state["players"] == ["p1"]


def test_channel_state_serialization() -> None:
    state = ChannelState({"current_location_id": "r"})
    serialized = state.to_dict()
    assert isinstance(serialized, dict)
    assert not isinstance(serialized, ChannelState)
    assert serialized["current_location_id"] == "r"
    restored = ChannelState.from_dict(serialized)
    assert restored.current_location_id == "r"


def test_repository_get_state_returns_channel_state() -> None:
    repo = ChannelRepository(db)
    state = repo.get_state("channel_state_test")
    assert isinstance(state, ChannelState)
    assert state.campaign_id == "default"

    repo.set_location("channel_state_test", "room_x")
    again = repo.get_state("channel_state_test")
    assert isinstance(again, ChannelState)
    assert again.current_location_id == "room_x"