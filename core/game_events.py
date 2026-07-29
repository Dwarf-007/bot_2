"""
CORE/GAME_EVENTS.PY
Canonical synchronous event model and in-process event bus for the AI DM engine.

Design goals:
- One single event contract for the whole engine.
- Lightweight and Oracle/VPS friendly.
- No Discord, DB, LLM, or async dependency in this module.
- Handlers may return command/output objects; EventBus.emit() collects them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Callable, DefaultDict, Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameEvent:
    """
    Canonical domain event.

    Attributes:
        type: Stable event type string from EventTypes.
        payload: JSON-serializable event data.
    """

    type: str
    payload: Dict[str, Any] = field(default_factory=dict)


class EventTypes:
    """
    Canonical event type registry.

    Keep these as plain strings for easy JSON persistence and SQLite storage.
    """

    # Generic state / movement
    STATE_CHANGED = "state_changed"
    PLAYER_MOVED = "player_moved"
    ROOM_ENTERED = "room_entered"

    # Combat lifecycle
    COMBAT_START = "combat_start"
    COMBAT_STARTED = COMBAT_START  # Backward-compatible alias
    COMBAT_END = "combat_end"
    COMBAT_ENDED = COMBAT_END      # Backward-compatible alias
    ALL_MONSTERS_DEFEATED = "all_monsters_defeated"
    PLAYER_ROLL = "player_roll"

    # Mechanical consequences
    DAMAGE = "damage"
    REQUIRED_CHECK = "required_check"

    # Rest lifecycle
    REST_REQUESTED = "rest_requested"
    REST_REQUEST = REST_REQUESTED  # Backward-compatible alias
    REST_COMPLETED = "rest_completed"
    REST_SUCCESS = REST_COMPLETED  # Backward-compatible alias
    REST_INTERRUPTED = "rest_interrupted"

    # Rewards / inventory / memory
    XP_GAINED = "xp_gained"
    INVENTORY_UPDATED = "inventory_updated"
    ITEM_GAINED = "item_gained"
    NPC_INTERACTION = "npc_interaction"
    TRAP_TRIGGERED = "trap_triggered"


EventHandler = Callable[[GameEvent], Any]


class EventBus:
    """
    Lightweight synchronous event dispatcher.

    Usage:
        bus = EventBus()
        bus.register(EventTypes.DAMAGE, DamageEventHandler().handle)
        results = bus.emit(GameEvent(EventTypes.DAMAGE, {"amount": 5}))

    Notes:
        - Exceptions in one handler are logged and do not stop the remaining handlers.
        - None return values are ignored.
        - List return values are flattened one level for convenience.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[EventHandler]] = defaultdict(list)

    def register(self, event_type: str, handler: EventHandler) -> None:
        if not event_type:
            raise ValueError("event_type must be a non-empty string")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: GameEvent | str, payload: Dict[str, Any] | None = None) -> List[Any]:
        normalized_event = self._normalize_event(event, payload)
        results: List[Any] = []

        for handler in list(self._handlers.get(normalized_event.type, [])):
            try:
                result = handler(normalized_event)
            except Exception:
                logger.exception(
                    "Event handler failed for event_type=%s handler=%r",
                    normalized_event.type,
                    handler,
                )
                continue

            if result is None:
                continue
            if isinstance(result, list):
                results.extend(item for item in result if item is not None)
            else:
                results.append(result)

        return results

    @staticmethod
    def _normalize_event(event: GameEvent | str, payload: Dict[str, Any] | None) -> GameEvent:
        if isinstance(event, GameEvent):
            return event
        if isinstance(event, str):
            return GameEvent(type=event, payload=payload or {})
        raise TypeError("event must be a GameEvent or event type string")
