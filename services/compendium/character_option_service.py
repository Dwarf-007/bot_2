"""
SERVICES/COMPENDIUM/CHARACTER_OPTION_SERVICE.PY
Advisory character-option lookup service built on CompendiumIndexService.

F1.8 purpose:
- Provide the first character-building facade over the compendium index.
- Lookup classes, subclasses, species/races, backgrounds, feats, and character
  options.
- Extract class/subclass level features when the raw 5etools-style payload makes
  them available.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Not an authoritative character sheet engine.
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


CHARACTER_OPTION_TYPES = [
    CompendiumEntryType.CLASS,
    CompendiumEntryType.SUBCLASS,
    CompendiumEntryType.SPECIES,
    CompendiumEntryType.BACKGROUND,
    CompendiumEntryType.FEAT,
    CompendiumEntryType.RULE,
]


@dataclass(frozen=True)
class CharacterOptionMatch:
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
class CharacterOptionResult:
    query: str
    found: bool
    matches: List[CharacterOptionMatch] = field(default_factory=list)
    advisory_text: str = ""


@dataclass(frozen=True)
class ClassLevelFeature:
    name: str
    class_name: str
    level: int
    source: str = ""
    entry_id: str = ""
    snippet: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassLevelFeatureResult:
    class_name: str
    level: int
    found: bool
    features: List[ClassLevelFeature] = field(default_factory=list)


class CharacterOptionService:
    """Advisory facade for character option lookup and class feature discovery."""

    def __init__(
        self,
        index: CompendiumIndexService,
        source_policy: SourcePolicy | None = None,
        default_limit: int = 5,
        max_snippet_chars: int = 320,
    ) -> None:
        self.index = index
        self.source_policy = source_policy
        self.default_limit = int(default_limit or 5)
        self.max_snippet_chars = int(max_snippet_chars or 320)

    def lookup_option(
        self,
        text: str,
        entry_types: Optional[Iterable[CompendiumEntryType | str]] = None,
        limit: Optional[int] = None,
        source_policy: Optional[SourcePolicy] = None,
    ) -> CharacterOptionResult:
        query_text = str(text or "").strip()
        if not query_text:
            return CharacterOptionResult(query="", found=False, advisory_text="Nem kaptam karakteropció keresési kifejezést.")

        query = CompendiumQuery(
            text=query_text,
            entry_types=list(entry_types or CHARACTER_OPTION_TYPES),
            limit=limit or self.default_limit,
        )
        search_results = self.index.search(query, source_policy=source_policy or self.source_policy)
        matches = [self._to_match(result) for result in search_results]
        return CharacterOptionResult(
            query=query_text,
            found=bool(matches),
            matches=matches,
            advisory_text=self._build_advisory_text(query_text, matches),
        )

    def lookup_class(self, class_name: str, limit: Optional[int] = None) -> CharacterOptionResult:
        return self.lookup_option(class_name, entry_types=[CompendiumEntryType.CLASS], limit=limit)

    def lookup_subclass(self, subclass_name: str, limit: Optional[int] = None) -> CharacterOptionResult:
        return self.lookup_option(subclass_name, entry_types=[CompendiumEntryType.SUBCLASS], limit=limit)

    def lookup_species(self, species_name: str, limit: Optional[int] = None) -> CharacterOptionResult:
        return self.lookup_option(species_name, entry_types=[CompendiumEntryType.SPECIES], limit=limit)

    def lookup_background(self, background_name: str, limit: Optional[int] = None) -> CharacterOptionResult:
        return self.lookup_option(background_name, entry_types=[CompendiumEntryType.BACKGROUND], limit=limit)

    def lookup_feat(self, feat_name: str, limit: Optional[int] = None) -> CharacterOptionResult:
        return self.lookup_option(feat_name, entry_types=[CompendiumEntryType.FEAT], limit=limit)

    def get_class_level_features(
        self,
        class_name: str,
        level: int,
        subclass_name: Optional[str] = None,
    ) -> ClassLevelFeatureResult:
        """Return class/subclass features for a specific class level.

        Supports two common shapes:
        1. class entry raw contains classFeatures/features with level data.
        2. separate classFeature/subclassFeature entries were indexed as RULE entries
           with raw.className/raw.level metadata.
        """
        safe_class_name = str(class_name or "").strip()
        safe_subclass_name = str(subclass_name or "").strip()
        safe_level = int(level)
        if not safe_class_name or safe_level <= 0:
            return ClassLevelFeatureResult(class_name=safe_class_name, level=safe_level, found=False)

        features: List[ClassLevelFeature] = []
        class_entries = self.index.search(
            CompendiumQuery(text=safe_class_name, entry_types=[CompendiumEntryType.CLASS], limit=3),
            source_policy=self.source_policy,
        )
        for result in class_entries:
            if result.entry.name.lower() == safe_class_name.lower():
                features.extend(self._extract_features_from_class_entry(result.entry, safe_level))

        features.extend(self._extract_features_from_indexed_feature_entries(safe_class_name, safe_level, safe_subclass_name))
        features = self._dedupe_features(features)
        return ClassLevelFeatureResult(
            class_name=safe_class_name,
            level=safe_level,
            found=bool(features),
            features=features,
        )

    def _extract_features_from_class_entry(self, entry: CompendiumEntry, level: int) -> List[ClassLevelFeature]:
        raw = entry.raw or {}
        candidates: List[Any] = []
        for key in ("classFeatures", "features", "entries"):
            value = raw.get(key)
            if isinstance(value, list):
                candidates.extend(value)
        return [feature for feature in (self._feature_from_value(value, entry.name, level, entry) for value in candidates) if feature]

    def _extract_features_from_indexed_feature_entries(
        self,
        class_name: str,
        level: int,
        subclass_name: str = "",
    ) -> List[ClassLevelFeature]:
        features: List[ClassLevelFeature] = []
        for entry in self.index.list_entries():
            raw = entry.raw or {}
            raw_level = self._extract_level(raw)
            if raw_level != level:
                continue
            raw_class_name = str(raw.get("className") or raw.get("class") or raw.get("class_name") or "").strip()
            if raw_class_name and raw_class_name.lower() != class_name.lower():
                continue
            raw_subclass_name = str(raw.get("subclassShortName") or raw.get("subclassName") or raw.get("subclass") or "").strip()
            if subclass_name and raw_subclass_name and raw_subclass_name.lower() != subclass_name.lower():
                continue
            if entry.entry_type not in {CompendiumEntryType.RULE, CompendiumEntryType.CLASS, CompendiumEntryType.SUBCLASS}:
                continue
            features.append(ClassLevelFeature(
                name=entry.name,
                class_name=raw_class_name or class_name,
                level=level,
                source=entry.source,
                entry_id=entry.entry_id,
                snippet=self._extract_snippet(entry),
                raw=dict(raw),
            ))
        return features

    def _feature_from_value(self, value: Any, class_name: str, level: int, source_entry: CompendiumEntry) -> Optional[ClassLevelFeature]:
        if isinstance(value, str):
            # 5etools references often look like "Ability Score Improvement|Fighter|PHB|4".
            parts = [part.strip() for part in value.split("|")]
            name = parts[0] if parts else value
            ref_level = self._extract_level_from_parts(parts)
            if ref_level is not None and ref_level != level:
                return None
            if ref_level is None and str(level) not in value:
                return None
            return ClassLevelFeature(
                name=name,
                class_name=class_name,
                level=level,
                source=source_entry.source,
                entry_id=source_entry.entry_id,
                snippet="",
                raw={"reference": value},
            )
        if isinstance(value, dict):
            raw_level = self._extract_level(value)
            if raw_level != level:
                return None
            name = str(value.get("name") or value.get("featureName") or "Class Feature").strip()
            synthetic_entry = CompendiumEntry(
                entry_id=source_entry.entry_id,
                name=name,
                entry_type=CompendiumEntryType.RULE,
                source=source_entry.source,
                raw=dict(value),
            )
            return ClassLevelFeature(
                name=name,
                class_name=class_name,
                level=level,
                source=source_entry.source,
                entry_id=source_entry.entry_id,
                snippet=self._extract_snippet(synthetic_entry),
                raw=dict(value),
            )
        return None

    @staticmethod
    def _extract_level(raw: dict[str, Any]) -> Optional[int]:
        for key in ("level", "classFeatureLevel"):
            value = raw.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return None

    @staticmethod
    def _extract_level_from_parts(parts: List[str]) -> Optional[int]:
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None

    def _to_match(self, result: CompendiumSearchResult) -> CharacterOptionMatch:
        entry = result.entry
        return CharacterOptionMatch(
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
    def _dedupe_features(features: List[ClassLevelFeature]) -> List[ClassLevelFeature]:
        seen = set()
        result = []
        for feature in features:
            key = (feature.name.lower(), feature.class_name.lower(), feature.level, feature.source.lower())
            if key in seen:
                continue
            seen.add(key)
            result.append(feature)
        return result

    @staticmethod
    def _build_advisory_text(query: str, matches: List[CharacterOptionMatch]) -> str:
        if not matches:
            return f"Nem találtam karakteropció találatot erre: {query}"
        primary = matches[0]
        source = f" ({primary.source})" if primary.source else ""
        page = f", p. {primary.page}" if primary.page is not None else ""
        snippet = f"{primary.snippet}" if primary.snippet else ""
        return (
            f"Talált karakteropció: {primary.name} [{primary.entry_type}]{source}{page}."
            f"Ez advisory jellegű összefoglaló; a végső karakterlapot a DM/player hagyja jóvá."
            f"{snippet}"
        )
