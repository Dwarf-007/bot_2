"""
SERVICES/COMPENDIUM/FIVEETOOLS_DATA_SOURCE.PY
Source adapter for user-provided/local 5etools-style JSON data.

F1.8 update:
- Adds classFeature/subclassFeature mapping as RULE entries so LevelUpAdvisor can
  discover level-up features when class files include these collections.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType


COLLECTION_TO_ENTRY_TYPE: dict[str, CompendiumEntryType] = {
    "monster": CompendiumEntryType.MONSTER,
    "spell": CompendiumEntryType.SPELL,
    "item": CompendiumEntryType.ITEM,
    "baseitem": CompendiumEntryType.ITEM,
    "magicvariant": CompendiumEntryType.ITEM,
    "class": CompendiumEntryType.CLASS,
    "subclass": CompendiumEntryType.SUBCLASS,
    "classfeature": CompendiumEntryType.RULE,
    "subclassfeature": CompendiumEntryType.RULE,
    "background": CompendiumEntryType.BACKGROUND,
    "feat": CompendiumEntryType.FEAT,
    "condition": CompendiumEntryType.CONDITION,
    "disease": CompendiumEntryType.CONDITION,
    "status": CompendiumEntryType.CONDITION,
    "race": CompendiumEntryType.SPECIES,
    "species": CompendiumEntryType.SPECIES,
    "book": CompendiumEntryType.BOOK,
    "adventure": CompendiumEntryType.ADVENTURE,
    "variantrule": CompendiumEntryType.RULE,
    "optionalfeature": CompendiumEntryType.RULE,
    "charoption": CompendiumEntryType.RULE,
    "table": CompendiumEntryType.RULE,
    "action": CompendiumEntryType.RULE,
    "skill": CompendiumEntryType.RULE,
    "sense": CompendiumEntryType.RULE,
    "language": CompendiumEntryType.RULE,
    "deck": CompendiumEntryType.RULE,
    "trap": CompendiumEntryType.RULE,
    "hazard": CompendiumEntryType.RULE,
    "object": CompendiumEntryType.RULE,
    "vehicle": CompendiumEntryType.RULE,
    "reward": CompendiumEntryType.RULE,
    "deity": CompendiumEntryType.RULE,
    "cult": CompendiumEntryType.RULE,
    "boon": CompendiumEntryType.RULE,
}

DEFAULT_RAW_ROOT = Path("data/compendium/fiveetools/raw")


@dataclass(frozen=True)
class FiveEToolsRawCollection:
    file_path: Path
    collection_name: str
    entry_type: CompendiumEntryType
    items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class FiveEToolsDataSourceSummary:
    root: str
    files_scanned: int
    collections_found: int
    entries_loaded: int
    missing_root: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class FiveEToolsDataSource:
    def __init__(self, raw_root: str | Path = DEFAULT_RAW_ROOT, source_system: str = "5etools") -> None:
        self.raw_root = Path(raw_root)
        self.source_system = source_system
        self.errors: List[str] = []

    def iter_json_files(self) -> Iterator[Path]:
        if not self.raw_root.exists():
            return
        for path in sorted(self.raw_root.rglob("*.json")):
            if path.is_file():
                yield path

    def load_json_file(self, path: str | Path) -> Any:
        file_path = Path(path)
        return json.loads(file_path.read_text(encoding="utf-8"))

    def iter_raw_collections(self) -> Iterator[FiveEToolsRawCollection]:
        self.errors.clear()
        for file_path in self.iter_json_files():
            try:
                data = self.load_json_file(file_path)
            except Exception as exc:
                self.errors.append(f"{file_path}: {exc!r}")
                continue
            for collection in self._extract_collections_from_data(file_path, data):
                yield collection

    def load_entries(self, entry_types: Optional[Iterable[CompendiumEntryType | str]] = None) -> List[CompendiumEntry]:
        wanted = self._normalize_entry_type_filter(entry_types)
        entries: List[CompendiumEntry] = []
        for collection in self.iter_raw_collections():
            if wanted and collection.entry_type.value not in wanted:
                continue
            for item in collection.items:
                entry = self._to_entry(collection, item)
                if entry is not None:
                    entries.append(entry)
        return entries

    def load_summary(self) -> FiveEToolsDataSourceSummary:
        files = list(self.iter_json_files()) if self.raw_root.exists() else []
        collections = list(self.iter_raw_collections()) if self.raw_root.exists() else []
        entries_loaded = sum(len(collection.items) for collection in collections)
        return FiveEToolsDataSourceSummary(
            root=str(self.raw_root),
            files_scanned=len(files),
            collections_found=len(collections),
            entries_loaded=entries_loaded,
            missing_root=not self.raw_root.exists(),
            errors=list(self.errors),
        )

    def _extract_collections_from_data(self, file_path: Path, data: Any) -> Iterator[FiveEToolsRawCollection]:
        if isinstance(data, list):
            guessed = self._guess_collection_from_path(file_path)
            if guessed:
                yield FiveEToolsRawCollection(file_path, guessed, COLLECTION_TO_ENTRY_TYPE[guessed], [item for item in data if isinstance(item, dict)])
            return
        if not isinstance(data, Mapping):
            return
        for key, value in data.items():
            normalized_key = str(key).strip().lower()
            if normalized_key not in COLLECTION_TO_ENTRY_TYPE:
                continue
            if not isinstance(value, list):
                continue
            yield FiveEToolsRawCollection(file_path, normalized_key, COLLECTION_TO_ENTRY_TYPE[normalized_key], [item for item in value if isinstance(item, dict)])

    def _to_entry(self, collection: FiveEToolsRawCollection, item: Dict[str, Any]) -> Optional[CompendiumEntry]:
        name = self._extract_name(item)
        if not name:
            return None
        source = str(item.get("source") or item.get("book") or "").strip()
        page = self._extract_page(item)
        rules_version = self._guess_rules_version(item, collection.file_path)
        return CompendiumEntry(
            entry_id=self._build_entry_id(collection.entry_type, name, source, rules_version),
            name=name,
            entry_type=collection.entry_type,
            source_system=self.source_system,
            source=source,
            page=page,
            rules_version=rules_version,
            aliases=self._extract_aliases(item),
            tags=self._build_tags(collection, item),
            summary=self._extract_summary(item),
            raw=dict(item),
        )

    @staticmethod
    def _extract_name(item: Mapping[str, Any]) -> str:
        for key in ("name", "monster_name", "featureName", "title", "id"):
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    @staticmethod
    def _extract_page(item: Mapping[str, Any]) -> Optional[int]:
        value = item.get("page")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _extract_aliases(item: Mapping[str, Any]) -> List[str]:
        aliases: List[str] = []
        for key in ("alias", "aliases", "srd", "basicRules"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                aliases.append(value.strip())
            elif isinstance(value, list):
                aliases.extend(str(alias).strip() for alias in value if str(alias).strip())
        return sorted(set(aliases), key=str.lower)

    @staticmethod
    def _extract_summary(item: Mapping[str, Any]) -> str:
        for key in ("summary", "short", "desc"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        entries = item.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, str) and entry.strip():
                    return entry.strip()
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if isinstance(name, str) and name.strip():
                        return name.strip()
        return ""

    def _build_tags(self, collection: FiveEToolsRawCollection, item: Mapping[str, Any]) -> List[str]:
        tags = {collection.entry_type.value, collection.collection_name}
        source = str(item.get("source") or "").strip()
        if source:
            tags.add(f"source:{source}")
        for key in ("level", "classFeatureLevel"):
            value = item.get(key)
            if value is not None:
                tags.add(f"level:{value}")
        school = item.get("school")
        if school:
            tags.add(f"school:{school}")
        class_name = item.get("className") or item.get("class")
        if class_name:
            tags.add(f"class:{class_name}")
        return sorted(tags)

    @staticmethod
    def _build_entry_id(entry_type: CompendiumEntryType, name: str, source: str, rules_version: str) -> str:
        parts = [entry_type.value, _slugify(name)]
        if source:
            parts.append(_slugify(source))
        if rules_version and rules_version != "unknown":
            parts.append(_slugify(rules_version))
        return ":".join(part for part in parts if part)

    @staticmethod
    def _guess_rules_version(item: Mapping[str, Any], file_path: Path) -> str:
        explicit = item.get("rules_version") or item.get("rulesVersion")
        if explicit:
            return str(explicit).strip()
        text = str(file_path).lower()
        source = str(item.get("source") or "").lower()
        if "2024" in text or "2024" in source or "xphb" in source or "xdmg" in source:
            return "2024"
        if "2014" in text or "2014" in source:
            return "2014"
        return "unknown"

    def _guess_collection_from_path(self, file_path: Path) -> Optional[str]:
        parts = [part.lower() for part in file_path.parts]
        name = file_path.stem.lower()
        candidates = list(reversed(parts)) + [name]
        for candidate in candidates:
            singular = candidate[:-1] if candidate.endswith("s") else candidate
            if candidate in COLLECTION_TO_ENTRY_TYPE:
                return candidate
            if singular in COLLECTION_TO_ENTRY_TYPE:
                return singular
        return None

    @staticmethod
    def _normalize_entry_type_filter(entry_types: Optional[Iterable[CompendiumEntryType | str]]) -> set[str]:
        if not entry_types:
            return set()
        result = set()
        for item in entry_types:
            value = item.value if isinstance(item, CompendiumEntryType) else str(item)
            if value.strip():
                result.add(value.strip().lower())
        return result


def _slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "entry"
