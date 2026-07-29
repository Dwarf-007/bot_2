"""
SUBSCRIBERS/MEMORY_LOGGING_SUBSCRIBER.PY
Thin EventBus subscriber wrapper for MemoryEventService.
"""

from __future__ import annotations

from core.game_events import GameEvent


class MemoryLoggingSubscriber:
    def __init__(self, memory_event_service) -> None:
        self.memory_event_service = memory_event_service

    def handle(self, event: GameEvent) -> None:
        self.memory_event_service.handle_event(event)
