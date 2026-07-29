"""
SERVICES/COMPENDIUM/SOURCE_POLICY.PY
Source filtering policy for advisory/reference compendium lookup.

The policy is intentionally explicit because the future compendium layer may
include multiple rule eras, licensed/user-provided content, homebrew, and
campaign-specific modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from services.compendium.compendium_models import CompendiumEntry


@dataclass(frozen=True)
class SourcePolicy:
    """Controls which sources/rules versions are eligible for lookup."""

    allowed_sources: List[str] = field(default_factory=list)
    blocked_sources: List[str] = field(default_factory=list)
    allow_homebrew: bool = True
    prefer_latest_rules: bool = False
    rules_version: Optional[str] = None

    def allows(self, entry: CompendiumEntry) -> bool:
        source = str(entry.source or "").strip().lower()
        source_system = str(entry.source_system or "").strip().lower()
        allowed = self._normalized(self.allowed_sources)
        blocked = self._normalized(self.blocked_sources)

        if source and source in blocked:
            return False
        if source_system == "homebrew" and not self.allow_homebrew:
            return False
        if allowed and source not in allowed:
            return False
        if self.rules_version and str(entry.rules_version or "").strip().lower() != self.rules_version.strip().lower():
            return False
        return True

    def filter_entries(self, entries: Iterable[CompendiumEntry]) -> List[CompendiumEntry]:
        return [entry for entry in entries if self.allows(entry)]

    @staticmethod
    def _normalized(values: Iterable[str]) -> set[str]:
        return {str(value).strip().lower() for value in values if str(value).strip()}
