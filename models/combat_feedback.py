"""
MODELS/COMBAT_FEEDBACK.PY
Typed models for Avrae combat feedback processing.

The bot does NOT track HP. Avrae remains authoritative.
These models only track whether the encounter lifecycle appears to be complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class CombatMonsterEntry:
    name: str
    remaining: int


@dataclass(frozen=True)
class CombatStateSnapshot:
    channel_id: str
    active: bool
    room_id: Optional[str]
    monsters: List[CombatMonsterEntry] = field(default_factory=list)
    xp_reward_total: int = 0


@dataclass(frozen=True)
class CombatFeedbackResult:
    combat_started: bool = False
    combat_ended: bool = False
    defeated_names: List[str] = field(default_factory=list)
    all_monsters_defeated: bool = False
    remaining_monsters: List[CombatMonsterEntry] = field(default_factory=list)
    roll_results: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
