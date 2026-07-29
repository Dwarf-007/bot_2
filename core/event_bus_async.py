
"""
ASYNC_EVENT_BUS.PY

Asynchronous event bus for reactive, concurrent systems.

Supports:
- async handlers
- concurrent execution (gather)
- safe exception handling
"""

import asyncio
from typing import Callable, Dict, List, Any, Awaitable


AsyncEventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class AsyncEventBus:
    """
    Asynchronous event dispatcher.

    Key features:
    - async/await compatible
    - concurrent handler execution
    - failure isolation per handler
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[AsyncEventHandler]] = {}

    def subscribe(self, event_name: str, handler: AsyncEventHandler) -> None:
        """
        Registers an async handler.
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(handler)

    async def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Dispatches event to all async subscribers concurrently.

        IMPORTANT:
        - does not block on individual handler failures
        - all handlers run concurrently
        """
        handlers = self._subscribers.get(event_name, [])

        if not handlers:
            return

        tasks = [
            self._safe_execute(handler, payload, event_name)
            for handler in handlers
        ]

        await asyncio.gather(*tasks)

    async def _safe_execute(
        self,
        handler: AsyncEventHandler,
        payload: Dict[str, Any],
        event_name: str
    ) -> None:
        """
        Executes a handler safely.
        Prevents one failure from breaking others.
        """
        try:
            await handler(payload)
        except Exception as e:
            print(f"[ASYNC EVENT ERROR] {event_name}: {e}")
