
"""
ENCOUNTER_MODELS.PY - Canonical structured models for encounter resolution.

This module contains typed domain objects only.
It does not perform I/O, database access, or Discord operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class EncounterUnit:
    """
    Represents one monster entry within a resolved encounter.

    Attributes:
        monster_name: Canonical monster name to be passed to Avrae.
        count: Number of monsters to spawn.
        source: Resolution source (e.g. ROOM, TABLE, FALLBACK).
    """

    monster_name: str
    count: int
    source: str = "ROOM"


@dataclass(frozen=True)
class EncounterResult:
    """
    Canonical encounter object returned by the resolver.

    Attributes:
        encounter_type: Encounter category (REST_AMBUSH, STATIC_ROOM, etc.).
        difficulty: Difficulty tier (EASY, STANDARD, HARD, DEADLY).
        units: Concrete monster groups to spawn.
        room_id: Optional room identifier.
        trigger_reason: Human-readable internal reason.
        narrative_hint: Optional short text for orchestration layers.
    """

    encounter_type: str
    difficulty: str
    units: List[EncounterUnit] = field(default_factory=list)
    room_id: Optional[str] = None
    trigger_reason: str = ""
    narrative_hint: Optional[str] = None
