"""
CORE/STATE_MACHINE.PY
Deterministic channel state transitions for the AI DM engine.
"""

from __future__ import annotations

from typing import Dict

from core.game_events import EventTypes, GameEvent
from core.game_state import GameState


class StateMachine:
    """
    Pure transition table.

    This class does not persist anything and does not emit events.
    Persistence/event emission belongs to StateOrchestrator.
    """

    TRANSITIONS: Dict[GameState, Dict[str, GameState]] = {
        GameState.EXPLORATION: {
            EventTypes.COMBAT_START: GameState.COMBAT,
            EventTypes.REST_REQUESTED: GameState.REST,
        },
        GameState.REST: {
            EventTypes.REST_COMPLETED: GameState.EXPLORATION,
            EventTypes.REST_INTERRUPTED: GameState.COMBAT,
            EventTypes.COMBAT_START: GameState.COMBAT,
        },
        GameState.COMBAT: {
            EventTypes.COMBAT_END: GameState.EXPLORATION,
            EventTypes.ALL_MONSTERS_DEFEATED: GameState.EXPLORATION,
        },
    }

    @classmethod
    def get_next_state(cls, current: GameState | str, event: GameEvent | str) -> GameState:
        current_state = cls._normalize_state(current)
        event_type = cls._normalize_event_type(event)
        return cls.TRANSITIONS.get(current_state, {}).get(event_type, current_state)

    @staticmethod
    def _normalize_state(current: GameState | str) -> GameState:
        if isinstance(current, GameState):
            return current
        try:
            return GameState(str(current))
        except ValueError:
            return GameState.EXPLORATION

    @staticmethod
    def _normalize_event_type(event: GameEvent | str) -> str:
        if isinstance(event, GameEvent):
            return event.type
        return str(event)
