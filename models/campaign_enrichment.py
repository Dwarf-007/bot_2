"""
MODELS/CAMPAIGN_ENRICHMENT.PY

Sprint 3 model layer for deterministic/optional-LLM campaign enrichment.

The enrichment output is intentionally JSON-friendly and can be merged into the
Sprint 2 campaign bundle files without changing repository schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EnrichedFaction:
    faction_id: str
    name: str
    agenda: str
    attitude: str = "unknown"
    rooms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnrichedQuest:
    quest_id: str
    title: str
    hook: str
    objective: str
    reward_hint: str = ""
    related_rooms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnrichedRoom:
    room_id: str
    boxed_text: str
    gm_notes: List[str] = field(default_factory=list)
    clues: List[str] = field(default_factory=list)
    complications: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignEnrichment:
    campaign_id: str
    campaign_name: str
    theme: str
    premise: str
    factions: List[EnrichedFaction] = field(default_factory=list)
    quests: List[EnrichedQuest] = field(default_factory=list)
    rooms: List[EnrichedRoom] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    rumors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "theme": self.theme,
            "premise": self.premise,
            "factions": [f.to_dict() for f in self.factions],
            "quests": [q.to_dict() for q in self.quests],
            "rooms": [r.to_dict() for r in self.rooms],
            "secrets": list(self.secrets),
            "rumors": list(self.rumors),
            "metadata": self.metadata,
        }
