"""
CORE/REST_MODELS.PY
Typed DTOs for deterministic rest handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RestIntent:
    requested: bool
    rest_type: str = "NONE"  # SHORT | LONG | NONE
    raw_text: str = ""


@dataclass(frozen=True)
class RestPolicy:
    allow_short_rest: bool = True
    allow_long_rest: bool = True
    interrupt_on_dangerous_room: bool = True
    default_ambush_monster: Optional[str] = None
    default_ambush_xp: int = 0


@dataclass(frozen=True)
class RestResolution:
    rest_type: str
    status: str  # SUCCESS | INTERRUPTED | DENIED | NONE
    reason: str = ""
    ambush_monsters: List[Dict[str, int | str]] = field(default_factory=list)
    xp_reward_total: int = 0
