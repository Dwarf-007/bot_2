"""services/avrae_dispatcher.py

Dispatch Avrae commands to a local Avrae HTTP runtime if reachable.
"""
from __future__ import annotations

from typing import List

from services.avrae_client import AvraeClient


class AvraeDispatcher:
    def __init__(self, client: AvraeClient | None = None) -> None:
        self.client = client or AvraeClient()

    def is_available(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    def dispatch_commands(self, commands: List[str]) -> dict:
        if not commands:
            return {"status": "no_commands"}
        return self.client.batch_commands(commands)
