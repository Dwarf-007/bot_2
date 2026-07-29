"""
CORE/LLM_RESPONSE.PY
Canonical normalized LLM output contract for the AI DM engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InventoryUpdate:
    gold: float = 0.0
    items: Dict[str, int] = field(default_factory=dict)
    ammo: Dict[str, int] = field(default_factory=dict)


@dataclass
class RestConsequence:
    rest_type: str = "NONE"
    status: str = "NONE"
    ambush_monster: Optional[str] = None


@dataclass
class CombatStartRequest:
    enabled: bool = False
    monsters: List[Dict[str, int | str]] = field(default_factory=list)
    xp_reward_total: int = 0
    encounter_type: str = "LLM_TRIGGERED"
    difficulty: str = "STANDARD"


@dataclass
class SecretMessage:
    player_id: str
    text: str


@dataclass
class LLMResponse:
    narrative: str = ""
    required_check: str = "None"
    dc: int = 0
    next_room_id: Optional[str] = None
    xp_reward: int = 0
    milestone_reached: bool = False
    inventory_update: InventoryUpdate = field(default_factory=InventoryUpdate)
    avrae_sync_damage: Optional[int] = None
    secret_messages: List[SecretMessage] = field(default_factory=list)
    rest_consequence: RestConsequence = field(default_factory=RestConsequence)
    combat_start: CombatStartRequest = field(default_factory=CombatStartRequest)
    confidence: str = "medium"
    source_usage: str = "source_based"
    needs_clarification: bool = False
    dm_notes: List[str] = field(default_factory=list)
