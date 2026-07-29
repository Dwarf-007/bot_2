"""
SERVICES/COMPENDIUM/SPELL_REFERENCE_SERVICE.PY
Advisory spell lookup service built on CompendiumIndexService.

F1.7 purpose:
- Provide the first spell-specific compendium facade.
- Query spell entries by name/alias/source/rules version.
- Return short, source-aware advisory spell summaries.
- Support basic spell filters such as level and school when present in tags/raw.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Do not reproduce long spell text. Keep snippets short and contextual.
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


@dataclass(frozen=True)
class SpellReferenceMatch:
    """Single source-aware spell lookup match."""

    name: str
    entry_id: str
    source: str = ""
    page: int | None = None
    rules_version: str = "unknown"
    level: int | None = None
    school: str = ""
    casting_time: str = ""
    range_text: str = ""
    duration: str = ""
    components: str = ""
    classes: List[str] = field(default_factory=list)
    score: float = 0.0
    match_reason: str = ""
    snippet: str = ""


@dataclass(frozen=True)
class SpellReferenceResult:
    """Spell lookup result returned to application services."""

    query: str
    found: bool
    matches: List[SpellReferenceMatch] = field(default_factory=list)
    advisory_text: str = ""


class SpellReferenceService:
    """Small advisory facade for spell lookup."""

    def __init__(
        self,
        index: CompendiumIndexService,
        source_policy: SourcePolicy | None = None,
        default_limit: int = 3,
        max_snippet_chars: int = 420,
    ) -> None:
        self.index = index
        self.source_policy = source_policy
        self.default_limit = int(default_limit or 3)
        self.max_snippet_chars = int(max_snippet_chars or 420)

    def lookup(
        self,
        text: str,
        limit: Optional[int] = None,
        source_policy: Optional[SourcePolicy] = None,
        level: Optional[int] = None,
        school: Optional[str] = None,
    ) -> SpellReferenceResult:
        """Lookup a spell by text, optionally filtering by level/school."""
        query_text = str(text or "").strip()
        if not query_text:
            return SpellReferenceResult(query="", found=False, advisory_text="Nem kaptam varázslat keresési kifejezést.")

        query = CompendiumQuery(
            text=query_text,
            entry_types=[CompendiumEntryType.SPELL],
            limit=max(limit or self.default_limit, self.default_limit),
        )
        search_results = self.index.search(query, source_policy=source_policy or self.source_policy)
        matches = [self._to_match(result) for result in search_results]
        matches = self._filter_matches(matches, level=level, school=school)
        matches = matches[: max(1, int(limit or self.default_limit))]
        advisory = self._build_advisory_text(query_text, matches)
        return SpellReferenceResult(
            query=query_text,
            found=bool(matches),
            matches=matches,
            advisory_text=advisory,
        )

    def lookup_by_level(self, level: int, limit: Optional[int] = None, source_policy: Optional[SourcePolicy] = None) -> SpellReferenceResult:
        """Return spells matching a level by searching the generated level tag."""
        safe_level = int(level)
        query = CompendiumQuery(
            text=f"level:{safe_level}",
            entry_types=[CompendiumEntryType.SPELL],
            limit=limit or self.default_limit,
        )
        results = self.index.search(query, source_policy=source_policy or self.source_policy)
        matches = [self._to_match(result) for result in results]
        matches = [match for match in matches if match.level == safe_level]
        return SpellReferenceResult(
            query=f"level:{safe_level}",
            found=bool(matches),
            matches=matches,
            advisory_text=self._build_advisory_text(f"level:{safe_level}", matches),
        )

    def _to_match(self, result: CompendiumSearchResult) -> SpellReferenceMatch:
        entry = result.entry
        raw = entry.raw or {}
        return SpellReferenceMatch(
            name=entry.name,
            entry_id=entry.entry_id,
            source=entry.source,
            page=entry.page,
            rules_version=entry.rules_version,
            level=self._extract_level(entry),
            school=self._extract_school(entry),
            casting_time=self._format_time(raw.get("time")),
            range_text=self._format_range(raw.get("range")),
            duration=self._format_duration(raw.get("duration")),
            components=self._format_components(raw.get("components")),
            classes=self._extract_classes(raw),
            score=result.score,
            match_reason=result.match_reason,
            snippet=self._extract_snippet(entry),
        )

    def _filter_matches(
        self,
        matches: List[SpellReferenceMatch],
        level: Optional[int] = None,
        school: Optional[str] = None,
    ) -> List[SpellReferenceMatch]:
        result = matches
        if level is not None:
            safe_level = int(level)
            result = [match for match in result if match.level == safe_level]
        if school:
            normalized_school = str(school).strip().lower()
            result = [match for match in result if match.school.lower() == normalized_school]
        return result

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
    def _extract_level(entry: CompendiumEntry) -> int | None:
        raw = entry.raw or {}
        value = raw.get("level")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        for tag in entry.tags:
            text = str(tag)
            if text.startswith("level:"):
                maybe = text.split(":", 1)[1]
                if maybe.isdigit():
                    return int(maybe)
        return None

    @staticmethod
    def _extract_school(entry: CompendiumEntry) -> str:
        raw = entry.raw or {}
        value = raw.get("school")
        if value is not None:
            return str(value).strip()
        for tag in entry.tags:
            text = str(tag)
            if text.startswith("school:"):
                return text.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _format_time(value: Any) -> str:
        if isinstance(value, list) and value:
            item = value[0]
            if isinstance(item, dict):
                number = item.get("number", "")
                unit = item.get("unit", "")
                return " ".join(str(part) for part in [number, unit] if str(part).strip())
        if isinstance(value, str):
            return value.strip()
        return ""

    @staticmethod
    def _format_range(value: Any) -> str:
        if isinstance(value, dict):
            range_type = value.get("type")
            distance = value.get("distance")
            if isinstance(distance, dict):
                amount = distance.get("amount")
                unit = distance.get("type")
                if amount is not None and unit:
                    return f"{amount} {unit}"
                if unit:
                    return str(unit)
            return str(range_type or "").strip()
        if isinstance(value, str):
            return value.strip()
        return ""

    @staticmethod
    def _format_duration(value: Any) -> str:
        if isinstance(value, list) and value:
            item = value[0]
            if isinstance(item, dict):
                duration_type = item.get("type", "")
                duration = item.get("duration")
                if isinstance(duration, dict):
                    amount = duration.get("amount")
                    unit = duration.get("type")
                    if amount is not None and unit:
                        return f"{amount} {unit}"
                return str(duration_type or "").strip()
        if isinstance(value, str):
            return value.strip()
        return ""

    @staticmethod
    def _format_components(value: Any) -> str:
        if isinstance(value, dict):
            parts = []
            for key, label in (("v", "V"), ("s", "S"), ("m", "M")):
                if key in value and value[key]:
                    if key == "m" and isinstance(value[key], str):
                        parts.append(f"M ({value[key]})")
                    elif key == "m" and isinstance(value[key], dict):
                        text = value[key].get("text") or "material"
                        parts.append(f"M ({text})")
                    else:
                        parts.append(label)
            return ", ".join(parts)
        if isinstance(value, str):
            return value.strip()
        return ""

    @staticmethod
    def _extract_classes(raw: dict[str, Any]) -> List[str]:
        classes = raw.get("classes")
        result: List[str] = []
        if isinstance(classes, dict):
            from_class_list = classes.get("fromClassList") or classes.get("fromClassListVariant") or []
            if isinstance(from_class_list, list):
                for item in from_class_list:
                    if isinstance(item, dict):
                        name = item.get("name")
                        if name:
                            result.append(str(name))
                    elif isinstance(item, str):
                        result.append(item)
        return sorted(set(result), key=str.lower)

    @staticmethod
    def _build_advisory_text(query: str, matches: List[SpellReferenceMatch]) -> str:
        if not matches:
            return f"Nem találtam varázslat találatot erre: {query}"

        primary = matches[0]
        level = "cantrip" if primary.level == 0 else f"level {primary.level}" if primary.level is not None else "unknown level"
        school = f", {primary.school}" if primary.school else ""
        source = f" ({primary.source})" if primary.source else ""
        page = f", p. {primary.page}" if primary.page is not None else ""
        meta = f"{level}{school}{source}{page}"
        snippet = f"{primary.snippet}" if primary.snippet else ""
        return (
            f"Talált varázslatreferencia: {primary.name} — {meta}."
            f"Ez advisory jellegű összefoglaló; a végső döntés a DM-é."
            f"{snippet}"
        )
