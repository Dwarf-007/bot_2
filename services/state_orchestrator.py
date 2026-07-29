"""
SERVICES/STATE_ORCHESTRATOR.PY
Coordinates deterministic state transitions, persistence, and state_changed events.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.game_events import EventBus, EventTypes, GameEvent
from core.game_state import GameState
from core.state_machine import StateMachine


class StateOrchestrator:
    """
    Thin application service around StateMachine.

    Dependencies:
        channel_repo:
            Must provide get_state(channel_id) and set_state(channel_id, state).
        event_bus:
            Canonical EventBus from core.game_events.
    """

    def __init__(self, channel_repo, event_bus: EventBus) -> None:
        self.channel_repo = channel_repo
        self.event_bus = event_bus

    def transition(
        self,
        channel_id: str,
        event: GameEvent | str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> GameState:
        state_data = self.channel_repo.get_state(channel_id) or {}
        current = self._extract_current_state(state_data)
        normalized_event = self._normalize_event(event, payload)
        next_state = StateMachine.get_next_state(current, normalized_event)

        if next_state != current:
            self.channel_repo.set_state(channel_id, next_state.value)
            self.event_bus.emit(
                GameEvent(
                    type=EventTypes.STATE_CHANGED,
                    payload={
                        "channel_id": str(channel_id),
                        "from": current.value,
                        "to": next_state.value,
                        "event": normalized_event.type,
                        "event_payload": normalized_event.payload,
                    },
                )
            )

        return next_state

    @staticmethod
    def _extract_current_state(state_data: Dict[str, Any]) -> GameState:
        raw_state = state_data.get("current_state", GameState.EXPLORATION.value)
        try:
            return GameState(str(raw_state))
        except ValueError:
            return GameState.EXPLORATION

    @staticmethod
    def _normalize_event(event: GameEvent | str, payload: Optional[Dict[str, Any]]) -> GameEvent:
        if isinstance(event, GameEvent):
            return event
        return GameEvent(type=str(event), payload=payload or {})
