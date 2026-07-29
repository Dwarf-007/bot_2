
"""
EVENT_BUS.PY

Simple synchronous event bus for reactive architecture.
"""

from typing import Callable, Dict, List, Any


EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """
    Lightweight in-process event dispatcher.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """
        Registers a handler to an event.
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(handler)

    def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Dispatches event to all subscribers.

        NOTE:
        - synchronous
        - no return values
        """
        handlers = self._subscribers.get(event_name, [])

        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                print(f"[EVENT ERROR] {event_name}: {e}")
