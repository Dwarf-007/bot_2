"""
CORE/TRAP_CONSEQUENCE_MODELS.PY
Typed models for deterministic trap consequences.

The trap engine is intentionally deterministic and stateful. The LLM may narrate
afterwards, but the engine decides whether a trap consequence is produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TrapTriggerContext:
    room_id: str
    attempted_direction: Optional[str] = None
    failure_reason: str = ""
    player_id: Optional[str] = None
    action_text: str = ""


@dataclass(frozen=True)
class TrapDefinition:
    name: str
    trigger_on: List[str] = field(default_factory=list)
    damage: int = 0
    damage_type: str = ""
    required_check: str = "None"
    dc: int = 0
    effect_tags: List[str] = field(default_factory=list)
    once: bool = True
    description: str = ""


@dataclass(frozen=True)
class TrapTriggerResult:
    trap_name: str
    triggered: bool
    damage: int = 0
    damage_type: str = ""
    required_check: str = "None"
    dc: int = 0
    effect_tags: List[str] = field(default_factory=list)
    narrative_hint: str = ""


@dataclass(frozen=True)
class TrapEvaluationBundle:
    room_id: str
    triggered_results: List[TrapTriggerResult] = field(default_factory=list)
    updated_trap_state: Dict[str, Any] = field(default_factory=dict)
    debug_notes: List[str] = field(default_factory=list)
