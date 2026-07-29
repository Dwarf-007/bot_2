"""
SERVICES/COMPENDIUM/RULES_REFERENCE_SERVICE.PY
Advisory rules/conditions lookup service built on CompendiumIndexService.

F1.6 purpose:
- First non-combat compendium use case.
- Query rules, conditions, actions, skills, senses, languages, and variant rules.
- Return short, source-aware advisory lookup results.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Do not reproduce long book passages. Keep snippets short and contextual.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import (
    CompendiumEntry,
    CompendiumEntryType,
    CompendiumQuery,
    CompendiumSearchResult,
)
from services.compendium.source_policy import SourcePolicy


DEFAULT_RULE_ENTRY_TYPES = [
    CompendiumEntryType.RULE,
    CompendiumEntryType.CONDITION,
]


@dataclass(frozen=True)
class RulesReferenceMatch:
    """Single source-aware rules lookup match."""

    name: str
    entry_id: str
    entry_type: str
    source: str = ""
    page: int | None = None
    rules_version: str = "unknown"
    score: float = 0.0
    match_reason: str = ""
    snippet: str = ""


@dataclass(frozen=True)
class RulesReferenceResult:
    """Rules lookup result returned to application services."""

    query: str
    found: bool
    matches: List[RulesReferenceMatch] = field(default_factory=list)
    advisory_text: str = ""


class RulesReferenceService:
    """Small advisory facade for rule/condition lookup."""

    def __init__(
        self,
        index: CompendiumIndexService,
        source_policy: SourcePolicy | None = None,
        default_limit: int = 3,
        max_snippet_chars: int = 360,
    ) -> None:
        self.index = index
        self.source_policy = source_policy
        self.default_limit = int(default_limit or 3)
        self.max_snippet_chars = int(max_snippet_chars or 360)

    def lookup(
        self,
        text: str,
        limit: Optional[int] = None,
        source_policy: Optional[SourcePolicy] = None,
    ) -> RulesReferenceResult:
        """Lookup a rule/condition and return short advisory matches."""
        query_text = str(text or "").strip()
        if not query_text:
            return RulesReferenceResult(query="", found=False, advisory_text="Nem kaptam keresési kifejezést.")

        query = CompendiumQuery(
            text=query_text,
            entry_types=DEFAULT_RULE_ENTRY_TYPES,
            limit=limit or self.default_limit,
        )
        search_results = self.index.search(query, source_policy=source_policy or self.source_policy)
        matches = [self._to_match(result) for result in search_results]
        advisory = self._build_advisory_text(query_text, matches)
        return RulesReferenceResult(
            query=query_text,
            found=bool(matches),
            matches=matches,
            advisory_text=advisory,
        )

    def lookup_condition(self, text: str, limit: Optional[int] = None) -> RulesReferenceResult:
        """Condition-only lookup convenience wrapper."""
        query_text = str(text or "").strip()
        query = CompendiumQuery(
            text=query_text,
            entry_types=[CompendiumEntryType.CONDITION],
            limit=limit or self.default_limit,
        )
        results = self.index.search(query, source_policy=self.source_policy)
        matches = [self._to_match(result) for result in results]
        return RulesReferenceResult(
            query=query_text,
            found=bool(matches),
            matches=matches,
            advisory_text=self._build_advisory_text(query_text, matches),
        )

    def _to_match(self, result: CompendiumSearchResult) -> RulesReferenceMatch:
        entry = result.entry
        return RulesReferenceMatch(
            name=entry.name,
            entry_id=entry.entry_id,
            entry_type=str(entry.entry_type.value if isinstance(entry.entry_type, CompendiumEntryType) else entry.entry_type),
            source=entry.source,
            page=entry.page,
            rules_version=entry.rules_version,
            score=result.score,
            match_reason=result.match_reason,
            snippet=self._extract_snippet(entry),
        )

    def _extract_snippet(self, entry: CompendiumEntry) -> str:
        text = entry.summary.strip() if entry.summary else ""
        if not text:
            text = self._extract_text_from_raw(entry.raw)
        return self._truncate(text)

    def _extract_text_from_raw(self, raw: dict[str, Any]) -> str:
        for key in ("summary", "short", "desc"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        entries = raw.get("entries")
        if isinstance(entries, list):
            return self._flatten_entries(entries)
        return ""

    def _flatten_entries(self, entries: Iterable[Any]) -> str:
        parts: List[str] = []
        for entry in entries:
            if isinstance(entry, str):
                parts.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    parts.append(name.strip())
                nested = entry.get("entries")
                if isinstance(nested, list):
                    nested_text = self._flatten_entries(nested)
                    if nested_text:
                        parts.append(nested_text)
            if len(" ".join(parts)) >= self.max_snippet_chars:
                break
        return " ".join(part.strip() for part in parts if part.strip())

    def _truncate(self, text: str) -> str:
        clean = " ".join(str(text or "").split())
        if len(clean) <= self.max_snippet_chars:
            return clean
        return clean[: max(0, self.max_snippet_chars - 1)].rstrip() + "…"

    @staticmethod
    def _build_advisory_text(query: str, matches: List[RulesReferenceMatch]) -> str:
        if not matches:
            return f"Nem találtam szabály- vagy condition találatot erre: {query}"

        primary = matches[0]
        source = f" ({primary.source})" if primary.source else ""
        page = f", p. {primary.page}" if primary.page is not None else ""
        snippet = f"{primary.snippet}" if primary.snippet else ""
        return (
            f"Talált szabályreferencia: {primary.name}{source}{page}."
            f"Ez advisory jellegű összefoglaló; a végső döntés a DM-é."
            f"{snippet}"
        )
