"""
SERVICES/ASYNC_EVENT_BRIDGE.PY
Bridges the synchronous EventBus to async Discord subscriber methods.

EventBus handlers are synchronous by design. This bridge schedules async
subscriber callbacks on the running bot loop without blocking the game pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from core.game_events import GameEvent

logger = logging.getLogger(__name__)


class AsyncEventBridge:
    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self.loop = loop

    def wrap(self, async_handler: Callable[[GameEvent], Awaitable[None]]):
        def sync_handler(event: GameEvent):
            try:
                loop = self.loop or asyncio.get_running_loop()
                loop.create_task(self._safe_call(async_handler, event))
            except RuntimeError:
                logger.warning("No running event loop; async event handler skipped: %r", async_handler)
            return None

        return sync_handler

    @staticmethod
    async def _safe_call(async_handler: Callable[[GameEvent], Awaitable[None]], event: GameEvent) -> None:
        try:
            await async_handler(event)
        except Exception:
            logger.exception("Async event subscriber failed: %r", async_handler)
