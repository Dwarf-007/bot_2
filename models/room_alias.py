
"""
MODELS/ROOM_ALIAS.PY
Typed DTOs for room aliases/title lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RoomAliasRecord:
    campaign_id: str
    alias: str
    normalized_alias: str
    room_id: str
    title: Optional[str] = None
    source: str = "manual"
