"""
CORE/GAME_TURN.PY
Small DTOs for the game turn pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameTurnInput:
    channel_id: str
    player_id: str
    text: str


@dataclass(frozen=True)
class GameTurnTrace:
    channel_id: str
    player_id: str
    mode: str
    current_location_id: str | None
    used_llm: bool
