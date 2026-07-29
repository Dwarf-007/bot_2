"""
SERVICES/COMPENDIUM/COMPENDIUM_INDEX_SERVICE.PY
In-memory search/index service for source-agnostic compendium entries.

F1.4 purpose:
- Provide exact lookup, alias lookup, contains search, and simple ranked search.
- Support entry_type filtering.
- Support SourcePolicy filtering.
- Keep the index source-agnostic: entries may come from 5etools, SRD, homebrew,
  campaign modules, or future providers.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No copyrighted/full-text response generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from services.compendium.compendium_models import (
    CompendiumEntry,
    CompendiumEntryType,
    CompendiumQuery,
    CompendiumSearchResult,
)
from services.compendium.source_policy import SourcePolicy


@dataclass(frozen=True)
class CompendiumIndexStats:
    """Lightweight index diagnostics for smoke tests and admin/debug views."""

    entries: int
    names: int
    aliases: int
    entry_types: Dict[str, int] = field(default_factory=dict)


class CompendiumIndexService:
    """In-memory compendium search service."""

    def __init__(self, entries: Optional[Iterable[CompendiumEntry]] = None) -> None:
        self._entries: List[CompendiumEntry] = []
        self._by_id: Dict[str, CompendiumEntry] = {}
        self._by_name: Dict[str, List[CompendiumEntry]] = {}
        self._by_alias: Dict[str, List[CompendiumEntry]] = {}
        if entries:
            self.rebuild(entries)

    def rebuild(self, entries: Iterable[CompendiumEntry]) -> None:
        """Replace the index content with a new entry set."""
        self._entries = list(entries or [])
        self._by_id = {}
        self._by_name = {}
        self._by_alias = {}

        for entry in self._entries:
            self._by_id[entry.entry_id] = entry
            self._by_name.setdefault(_normalize(entry.name), []).append(entry)
            for alias in entry.aliases:
                normalized_alias = _normalize(alias)
                if normalized_alias:
                    self._by_alias.setdefault(normalized_alias, []).append(entry)

    def add_entries(self, entries: Iterable[CompendiumEntry]) -> None:
        """Add entries to the existing index."""
        self.rebuild([*self._entries, *(entries or [])])

    def list_entries(self) -> List[CompendiumEntry]:
        return list(self._entries)

    def get_by_id(self, entry_id: str) -> Optional[CompendiumEntry]:
        return self._by_id.get(str(entry_id or ""))

    def lookup_exact(
        self,
        text: str,
        entry_types: Optional[Iterable[CompendiumEntryType | str]] = None,
        source_policy: Optional[SourcePolicy] = None,
    ) -> List[CompendiumEntry]:
        """Return exact name or exact alias matches after filters."""
        key = _normalize(text)
        if not key:
            return []
        candidates = [*self._by_name.get(key, []), *self._by_alias.get(key, [])]
        return self._dedupe_and_filter(candidates, entry_types=entry_types, source_policy=source_policy)

    def search(
        self,
        query: CompendiumQuery | str,
        source_policy: Optional[SourcePolicy] = None,
    ) -> List[CompendiumSearchResult]:
        """Search entries using exact, alias, contains, and token matches."""
        if isinstance(query, str):
            query = CompendiumQuery(text=query)

        text = query.normalized_text()
        if not text:
            return []

        entry_types = query.entry_types
        policy = source_policy or SourcePolicy(
            allowed_sources=query.allowed_sources,
            allow_homebrew=query.include_homebrew,
            rules_version=query.rules_version,
        )

        results: List[CompendiumSearchResult] = []
        for entry in self._filter_entries(self._entries, entry_types=entry_types, source_policy=policy):
            score, reason = self._score_entry(text, entry)
            if score <= 0:
                continue
            results.append(CompendiumSearchResult(entry=entry, score=score, match_reason=reason))

        results.sort(key=lambda result: (-result.score, result.entry.name.lower(), result.entry.source.lower()))
        limit = max(1, int(query.limit or 5))
        return results[:limit]

    def stats(self) -> CompendiumIndexStats:
        by_type: Dict[str, int] = {}
        for entry in self._entries:
            entry_type = _entry_type_value(entry.entry_type)
            by_type[entry_type] = by_type.get(entry_type, 0) + 1
        return CompendiumIndexStats(
            entries=len(self._entries),
            names=len(self._by_name),
            aliases=sum(len(values) for values in self._by_alias.values()),
            entry_types=by_type,
        )

    def _score_entry(self, query: str, entry: CompendiumEntry) -> tuple[float, str]:
        name = _normalize(entry.name)
        aliases = [_normalize(alias) for alias in entry.aliases if _normalize(alias)]
        tags = [_normalize(tag) for tag in entry.tags if _normalize(tag)]
        summary = _normalize(entry.summary)

        if query == name:
            return 1.0, "exact_name"
        if query in aliases:
            return 0.95, "exact_alias"
        if name.startswith(query):
            return 0.85, "name_prefix"
        if query in name:
            return 0.75, "name_contains"
        if any(alias.startswith(query) for alias in aliases):
            return 0.70, "alias_prefix"
        if any(query in alias for alias in aliases):
            return 0.65, "alias_contains"
        if query in tags:
            return 0.55, "tag_match"
        if query and summary and query in summary:
            return 0.40, "summary_contains"

        query_tokens = _tokens(query)
        name_tokens = _tokens(name)
        if query_tokens and query_tokens.issubset(name_tokens):
            return 0.60, "name_token_subset"
        if query_tokens and any(token in tags for token in query_tokens):
            return 0.35, "tag_token_match"
        return 0.0, ""

    def _dedupe_and_filter(
        self,
        entries: Sequence[CompendiumEntry],
        entry_types: Optional[Iterable[CompendiumEntryType | str]] = None,
        source_policy: Optional[SourcePolicy] = None,
    ) -> List[CompendiumEntry]:
        seen = set()
        filtered = []
        for entry in self._filter_entries(entries, entry_types=entry_types, source_policy=source_policy):
            if entry.entry_id in seen:
                continue
            seen.add(entry.entry_id)
            filtered.append(entry)
        return filtered

    def _filter_entries(
        self,
        entries: Iterable[CompendiumEntry],
        entry_types: Optional[Iterable[CompendiumEntryType | str]] = None,
        source_policy: Optional[SourcePolicy] = None,
    ) -> List[CompendiumEntry]:
        wanted_types = {_entry_type_value(item) for item in (entry_types or []) if _entry_type_value(item)}
        result: List[CompendiumEntry] = []
        for entry in entries:
            if wanted_types and _entry_type_value(entry.entry_type) not in wanted_types:
                continue
            if source_policy and not source_policy.allows(entry):
                continue
            result.append(entry)
        return result


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalize(value)) if token}


def _entry_type_value(value: CompendiumEntryType | str) -> str:
    if isinstance(value, CompendiumEntryType):
        return value.value
    return str(value or "").strip().lower()
