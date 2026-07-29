"""
CORE/CHANNEL_STATE.PY
Typed, backward-compatible view over the persisted channel-state dict.

Channel state was previously accessed everywhere as a raw dict via
``get_state(channel_id).get("current_location_id")`` magic strings. This module
introduces a ``ChannelState`` model that *subclasses* ``dict`` so every existing
``state["key"]`` / ``state.get(...)`` access keeps working unchanged, while also
exposing typed attribute accessors (``state.current_location_id``,
``state.players``, ...) for clearer, safer call sites.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ChannelState(dict):
    """A channel-state dict with typed attribute accessors.

    Inherits from ``dict`` to remain a drop-in replacement for the previously
    returned raw ``dict`` (repository mutators and ``.get()`` callers are
    untouched). The typed properties below are convenience accessors that read
    and write the underlying dict keys.
    """

    # --- Typed accessors (mirror ChannelRepository.default_state keys) ---

    @property
    def campaign_id(self) -> str:
        return self.get("campaign_id") or "default"

    @campaign_id.setter
    def campaign_id(self, value: str) -> None:
        self["campaign_id"] = value

    @property
    def current_state(self) -> Optional[str]:
        return self.get("current_state")

    @current_state.setter
    def current_state(self, value: Optional[str]) -> None:
        self["current_state"] = value

    @property
    def current_location_id(self) -> Optional[str]:
        return self.get("current_location_id")

    @current_location_id.setter
    def current_location_id(self, value: Optional[str]) -> None:
        self["current_location_id"] = value

    @property
    def active_player(self) -> Optional[str]:
        return self.get("active_player")

    @active_player.setter
    def active_player(self, value: Optional[str]) -> None:
        self["active_player"] = value

    @property
    def players(self) -> List[str]:
        return self.get("players") or []

    @players.setter
    def players(self, value: List[str]) -> None:
        self["players"] = value

    @property
    def visited_rooms(self) -> List[str]:
        return self.get("visited_rooms") or []

    @visited_rooms.setter
    def visited_rooms(self, value: List[str]) -> None:
        self["visited_rooms"] = value

    @property
    def mode(self) -> Optional[str]:
        return self.get("mode")

    @mode.setter
    def mode(self, value: Optional[str]) -> None:
        self["mode"] = value

    @property
    def style(self) -> Optional[str]:
        return self.get("style")

    @style.setter
    def style(self, value: Optional[str]) -> None:
        self["style"] = value

    @property
    def difficulty(self) -> Optional[str]:
        return self.get("difficulty")

    @difficulty.setter
    def difficulty(self, value: Optional[str]) -> None:
        self["difficulty"] = value

    # --- Serialization helpers ---

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelState":
        return cls(data)