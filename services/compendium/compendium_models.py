"""
SERVICES/COMPENDIUM/COMPENDIUM_MODELS.PY
Source-agnostic compendium foundation models.

These models deliberately do not know whether data came from 5etools, SRD,
homebrew JSON, a campaign module, or another future provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompendiumEntryType(str, Enum):
    MONSTER = "monster"
    SPELL = "spell"
    ITEM = "item"
    RULE = "rule"
    CONDITION = "condition"
    CLASS = "class"
    SUBCLASS = "subclass"
    SPECIES = "species"
    BACKGROUND = "background"
    FEAT = "feat"
    ADVENTURE = "adventure"
    BOOK = "book"
    MODULE = "module"
    LOCATION = "location"
    NPC = "npc"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CompendiumEntry:
    """Normalized, source-agnostic compendium entry.

    The raw payload is preserved for later source-specific adapters, but the
    runtime should prefer the normalized fields for lookup, filtering, and
    advisory responses.
    """

    entry_id: str
    name: str
    entry_type: CompendiumEntryType | str
    source_system: str = "unknown"
    source: str = ""
    page: Optional[int] = None
    rules_version: str = "unknown"
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def normalized_name(self) -> str:
        return self.name.strip().lower()

    def normalized_aliases(self) -> List[str]:
        return [alias.strip().lower() for alias in self.aliases if str(alias).strip()]

    def matches_text(self, text: str) -> bool:
        query = str(text or "").strip().lower()
        if not query:
            return False
        if query == self.normalized_name():
            return True
        if query in self.normalized_aliases():
            return True
        return query in self.normalized_name()


@dataclass(frozen=True)
class CompendiumQuery:
    """Search/filter request passed to compendium services."""

    text: str
    entry_types: List[CompendiumEntryType | str] = field(default_factory=list)
    allowed_sources: List[str] = field(default_factory=list)
    rules_version: Optional[str] = None
    include_homebrew: bool = True
    limit: int = 5

    def normalized_text(self) -> str:
        return self.text.strip().lower()

    def normalized_entry_types(self) -> List[str]:
        return [str(item.value if isinstance(item, CompendiumEntryType) else item).strip().lower() for item in self.entry_types]

    def normalized_allowed_sources(self) -> List[str]:
        return [str(item).strip().lower() for item in self.allowed_sources if str(item).strip()]


@dataclass(frozen=True)
class CompendiumSearchResult:
    """Single search result with a score and explanation."""

    entry: CompendiumEntry
    score: float
    match_reason: str = ""

    def is_exact_match(self) -> bool:
        return self.match_reason == "exact_name" or self.score >= 1.0
