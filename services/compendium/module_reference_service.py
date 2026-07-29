"""
SERVICES/COMPENDIUM/MODULE_REFERENCE_SERVICE.PY
Advisory module/adventure/book content reference service.

F3.1 purpose:
- Start the Campaign Content Foundation for module/adventure/book based play.
- Search adventure/book/module entries and nested content nodes.
- Return short, source-aware references suitable for campaign runtime context.
- Move toward automated campaign running, while explicitly allowing DM approval
  or human assistance where full automation would be brittle, unsafe, or too
  expensive in complexity.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reproduce long adventure/book text.
- Does not make irreversible campaign decisions without DM/application approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import (
    CompendiumEntry,
    CompendiumEntryType,
    CompendiumQuery,
)
from services.compendium.source_policy import SourcePolicy


MODULE_ENTRY_TYPES = [
    CompendiumEntryType.ADVENTURE,
    CompendiumEntryType.BOOK,
    CompendiumEntryType.MODULE,
    CompendiumEntryType.LOCATION,
    CompendiumEntryType.NPC,
]


@dataclass(frozen=True)
class ModuleReferenceQuery:
    """Query for module/adventure/book content."""

    text: str
    module_name: str = ""
    source: str = ""
    entry_types: List[CompendiumEntryType | str] = field(default_factory=lambda: list(MODULE_ENTRY_TYPES))
    limit: int = 5
    max_snippet_chars: int = 480
    include_dm_review_notes: bool = True


@dataclass(frozen=True)
class ModuleContentNode:
    """Flattened content node extracted from nested adventure/book entries."""

    name: str
    path: List[str] = field(default_factory=list)
    depth: int = 0
    text: str = ""
    node_type: str = "entry"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def path_text(self) -> str:
        return " > ".join(part for part in self.path if part)


@dataclass(frozen=True)
class ModuleReferenceMatch:
    """Single source-aware module lookup match."""

    name: str
    entry_id: str
    entry_type: str
    source: str = ""
    page: int | None = None
    rules_version: str = "unknown"
    path: List[str] = field(default_factory=list)
    node_type: str = "entry"
    score: float = 0.0
    match_reason: str = ""
    snippet: str = ""
    requires_dm_review: bool = True
    automation_hint: str = ""

    @property
    def path_text(self) -> str:
        return " > ".join(part for part in self.path if part)


@dataclass(frozen=True)
class ModuleReferenceResult:
    """Module/adventure/book lookup result."""

    query: str
    found: bool
    matches: List[ModuleReferenceMatch] = field(default_factory=list)
    advisory_text: str = ""
    dm_review_recommended: bool = True


class ModuleReferenceService:
    """Advisory facade for module/adventure/book content lookup."""

    def __init__(
        self,
        index: CompendiumIndexService,
        source_policy: SourcePolicy | None = None,
        default_limit: int = 5,
        max_snippet_chars: int = 480,
    ) -> None:
        self.index = index
        self.source_policy = source_policy
        self.default_limit = int(default_limit or 5)
        self.max_snippet_chars = int(max_snippet_chars or 480)

    def lookup(self, query: ModuleReferenceQuery | str) -> ModuleReferenceResult:
        if isinstance(query, str):
            query = ModuleReferenceQuery(text=query, limit=self.default_limit, max_snippet_chars=self.max_snippet_chars)

        text = str(query.text or "").strip()
        if not text:
            return ModuleReferenceResult(
                query="",
                found=False,
                advisory_text="Nem kaptam modul/kampány keresési kifejezést.",
                dm_review_recommended=True,
            )

        entry_matches = self._search_entries(query)
        node_matches = self._search_nested_nodes(query)
        combined = self._dedupe_and_sort([*entry_matches, *node_matches])[: max(1, int(query.limit or self.default_limit))]
        advisory = self._build_advisory_text(query, combined)
        return ModuleReferenceResult(
            query=text,
            found=bool(combined),
            matches=combined,
            advisory_text=advisory,
            dm_review_recommended=any(match.requires_dm_review for match in combined) or query.include_dm_review_notes,
        )

    def lookup_section(self, module_name: str, section_name: str, limit: int = 5) -> ModuleReferenceResult:
        return self.lookup(ModuleReferenceQuery(text=section_name, module_name=module_name, limit=limit))

    def list_content_nodes(self, module_name: str = "") -> List[ModuleContentNode]:
        nodes: List[ModuleContentNode] = []
        for entry in self._candidate_entries(module_name=module_name):
            nodes.extend(self._extract_nodes(entry))
        return nodes

    def _search_entries(self, query: ModuleReferenceQuery) -> List[ModuleReferenceMatch]:
        compendium_results = self.index.search(
            CompendiumQuery(
                text=query.text,
                entry_types=query.entry_types,
                allowed_sources=[query.source] if query.source else [],
                limit=max(query.limit, self.default_limit),
            ),
            source_policy=self.source_policy,
        )
        matches: List[ModuleReferenceMatch] = []
        for result in compendium_results:
            entry = result.entry
            if query.module_name and query.module_name.lower() not in entry.name.lower() and query.module_name.lower() not in entry.entry_id.lower():
                continue
            matches.append(ModuleReferenceMatch(
                name=entry.name,
                entry_id=entry.entry_id,
                entry_type=self._entry_type_value(entry.entry_type),
                source=entry.source,
                page=entry.page,
                rules_version=entry.rules_version,
                path=[entry.name],
                node_type="entry",
                score=result.score,
                match_reason=result.match_reason,
                snippet=self._truncate(entry.summary or self._extract_text_from_raw(entry.raw), query.max_snippet_chars),
                requires_dm_review=True,
                automation_hint="Use as campaign context only. Ask the DM to confirm hidden information and next actions.",
            ))
        return matches

    def _search_nested_nodes(self, query: ModuleReferenceQuery) -> List[ModuleReferenceMatch]:
        normalized = query.text.strip().lower()
        matches: List[ModuleReferenceMatch] = []
        for entry in self._candidate_entries(module_name=query.module_name, source=query.source, entry_types=query.entry_types):
            for node in self._extract_nodes(entry):
                score, reason = self._score_node(normalized, node)
                if score <= 0:
                    continue
                snippet_source = node.text or self._node_raw_text(node.raw)
                matches.append(ModuleReferenceMatch(
                    name=node.name or entry.name,
                    entry_id=entry.entry_id,
                    entry_type=self._entry_type_value(entry.entry_type),
                    source=entry.source,
                    page=entry.page,
                    rules_version=entry.rules_version,
                    path=node.path or [entry.name],
                    node_type=node.node_type,
                    score=score,
                    match_reason=reason,
                    snippet=self._truncate(snippet_source, query.max_snippet_chars),
                    requires_dm_review=True,
                    automation_hint=self._automation_hint_for_node(node),
                ))
        return matches

    def _candidate_entries(
        self,
        module_name: str = "",
        source: str = "",
        entry_types: Optional[Iterable[CompendiumEntryType | str]] = None,
    ) -> List[CompendiumEntry]:
        wanted = {self._entry_type_value(item) for item in (entry_types or MODULE_ENTRY_TYPES)}
        module = module_name.strip().lower()
        source_key = source.strip().lower()
        entries = []
        for entry in self.index.list_entries():
            if self._entry_type_value(entry.entry_type) not in wanted:
                continue
            if source_key and entry.source.lower() != source_key:
                continue
            if module and module not in entry.name.lower() and module not in entry.entry_id.lower() and module not in str(entry.raw.get("id", "")).lower():
                continue
            if self.source_policy and not self.source_policy.allows(entry):
                continue
            entries.append(entry)
        return entries

    def _extract_nodes(self, entry: CompendiumEntry) -> List[ModuleContentNode]:
        raw = entry.raw or {}
        roots: List[Any] = []
        for key in ("entries", "data", "contents", "chapters", "sections"):
            value = raw.get(key)
            if isinstance(value, list):
                roots.extend(value)
            elif isinstance(value, dict):
                roots.append(value)
        nodes: List[ModuleContentNode] = []
        for root in roots:
            self._walk_node(root, parent_path=[entry.name], depth=0, out=nodes)
        return nodes

    def _walk_node(self, value: Any, parent_path: List[str], depth: int, out: List[ModuleContentNode]) -> None:
        if isinstance(value, str):
            out.append(ModuleContentNode(name=parent_path[-1] if parent_path else "Text", path=list(parent_path), depth=depth, text=value, node_type="text"))
            return
        if isinstance(value, list):
            for item in value:
                self._walk_node(item, parent_path=parent_path, depth=depth, out=out)
            return
        if not isinstance(value, dict):
            return

        name = str(value.get("name") or value.get("title") or value.get("id") or parent_path[-1] if parent_path else "Section").strip()
        node_type = str(value.get("type") or "entry")
        path = [*parent_path]
        if name and (not path or path[-1] != name):
            path.append(name)
        text = self._node_raw_text(value)
        out.append(ModuleContentNode(name=name, path=path, depth=depth, text=text, node_type=node_type, raw=dict(value)))

        for key in ("entries", "items", "data", "contents", "sections", "children"):
            nested = value.get(key)
            if isinstance(nested, (list, dict)):
                self._walk_node(nested, parent_path=path, depth=depth + 1, out=out)

    @staticmethod
    def _score_node(query: str, node: ModuleContentNode) -> tuple[float, str]:
        name = (node.name or "").lower()
        path = node.path_text.lower()
        text = (node.text or "").lower()
        if query == name:
            return 0.98, "exact_node_name"
        if name.startswith(query):
            return 0.88, "node_name_prefix"
        if query in name:
            return 0.78, "node_name_contains"
        if query in path:
            return 0.70, "path_contains"
        if query in text:
            return 0.45, "text_contains"
        return 0.0, ""

    @staticmethod
    def _automation_hint_for_node(node: ModuleContentNode) -> str:
        node_type = node.node_type.lower()
        if node_type in {"section", "entries", "entry"}:
            return "Suitable as scene/module context. DM should approve hidden information before revealing it."
        if node_type in {"table", "list"}:
            return "Use as structured reference. Human/DM review is recommended before applying results."
        return "Use as advisory context. Ask for DM approval when the next step changes campaign state."

    @staticmethod
    def _node_raw_text(raw: dict[str, Any]) -> str:
        parts: List[str] = []
        for key in ("text", "summary", "desc"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        entries = raw.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, str):
                    parts.append(entry.strip())
                elif isinstance(entry, dict):
                    name = entry.get("name")
                    if isinstance(name, str):
                        parts.append(name.strip())
                if len(" ".join(parts)) > 500:
                    break
        return " ".join(part for part in parts if part)

    @staticmethod
    def _extract_text_from_raw(raw: dict[str, Any]) -> str:
        return ModuleReferenceService._node_raw_text(raw)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        clean = " ".join(str(text or "").split())
        safe_limit = max(80, int(limit or 480))
        if len(clean) <= safe_limit:
            return clean
        return clean[: safe_limit - 1].rstrip() + "…"

    @staticmethod
    def _dedupe_and_sort(matches: List[ModuleReferenceMatch]) -> List[ModuleReferenceMatch]:
        seen = set()
        result = []
        for match in sorted(matches, key=lambda item: (-item.score, item.name.lower(), item.path_text.lower())):
            key = (match.entry_id, tuple(match.path), match.snippet)
            if key in seen:
                continue
            seen.add(key)
            result.append(match)
        return result

    @staticmethod
    def _entry_type_value(value: CompendiumEntryType | str) -> str:
        if isinstance(value, CompendiumEntryType):
            return value.value
        return str(value or "").strip().lower()

    @staticmethod
    def _build_advisory_text(query: ModuleReferenceQuery, matches: List[ModuleReferenceMatch]) -> str:
        if not matches:
            return f"Nem találtam kampány/modul referenciát erre: {query.text}"
        primary = matches[0]
        source = f" ({primary.source})" if primary.source else ""
        page = f", p. {primary.page}" if primary.page is not None else ""
        path = f"\nPath: {primary.path_text}" if primary.path_text else ""
        snippet = f"\n{primary.snippet}" if primary.snippet else ""
        review = "\nDM review recommended before revealing hidden or state-changing information." if query.include_dm_review_notes else ""
        return (
            f"Talált kampány/modul referencia: {primary.name}{source}{page}."
            f"{path}"
            f"\nAutomation hint: {primary.automation_hint}"
            f"{review}"
            f"{snippet}"
        )
