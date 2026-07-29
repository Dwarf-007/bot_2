"""
SERVICES/COMPENDIUM/CAMPAIGN_CONTENT_ADVISOR.PY
Classifies module/adventure content into campaign-running advisory buckets.

F3.3 purpose:
- Interpret ModuleReferenceService nodes beyond simple lookup.
- Identify read-aloud candidates, encounter hints, trap hints, treasure hints,
  NPC hints, development/outcome hints, and reward/XP hints.
- Separate player-visible candidates from DM-only notes and approval checkpoints.
- Move toward automated campaign running while keeping human/DM review where
  hidden information, branching consequences, or state mutations are involved.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reproduce long adventure/book text.
- Does not mutate campaign state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional

from services.compendium.module_reference_service import (
    ModuleContentNode,
    ModuleReferenceQuery,
    ModuleReferenceService,
)


class CampaignContentKind(str, Enum):
    READ_ALOUD = "read_aloud_candidate"
    PLAYER_VISIBLE = "player_visible_candidate"
    DM_SECRET = "dm_secret"
    ENCOUNTER = "encounter_hint"
    TRAP = "trap_hint"
    TREASURE = "treasure_hint"
    NPC = "npc_hint"
    DEVELOPMENT = "development_hint"
    REWARD = "reward_hint"
    APPROVAL = "approval_required"
    GENERAL = "general_context"


@dataclass(frozen=True)
class CampaignContentHint:
    kind: CampaignContentKind | str
    title: str
    path: List[str] = field(default_factory=list)
    snippet: str = ""
    source: str = ""
    page: int | None = None
    requires_dm_review: bool = True
    confidence: float = 0.5
    extracted_entities: List[str] = field(default_factory=list)
    automation_hint: str = ""

    @property
    def path_text(self) -> str:
        return " > ".join(part for part in self.path if part)


@dataclass(frozen=True)
class CampaignContentAdvice:
    query: str
    found: bool
    player_visible_candidates: List[CampaignContentHint] = field(default_factory=list)
    dm_only_notes: List[CampaignContentHint] = field(default_factory=list)
    read_aloud_candidates: List[CampaignContentHint] = field(default_factory=list)
    encounter_hints: List[CampaignContentHint] = field(default_factory=list)
    trap_hints: List[CampaignContentHint] = field(default_factory=list)
    treasure_hints: List[CampaignContentHint] = field(default_factory=list)
    npc_hints: List[CampaignContentHint] = field(default_factory=list)
    development_hints: List[CampaignContentHint] = field(default_factory=list)
    reward_hints: List[CampaignContentHint] = field(default_factory=list)
    approval_checkpoints: List[str] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)
    advisory_text: str = ""


class CampaignContentAdvisor:
    """Builds structured advisory classifications from module content nodes."""

    CREATURE_TAG_RE = re.compile(r"\{@creature\s+([^}|]+)", re.IGNORECASE)
    ITEM_TAG_RE = re.compile(r"\{@item\s+([^}|]+)", re.IGNORECASE)
    CONDITION_TAG_RE = re.compile(r"\{@condition\s+([^}|]+)", re.IGNORECASE)
    DC_RE = re.compile(r"\{@dc\s+(\d+)\}|DC\s+(\d+)", re.IGNORECASE)
    DAMAGE_RE = re.compile(r"\{@damage\s+([^}]+)\}|\d+d\d+(?:[+-]\d+)?", re.IGNORECASE)
    XP_RE = re.compile(r"(\d+)\s*XP", re.IGNORECASE)

    def __init__(
        self,
        module_reference: ModuleReferenceService,
        max_snippet_chars: int = 420,
    ) -> None:
        self.module_reference = module_reference
        self.max_snippet_chars = int(max_snippet_chars or 420)

    def advise(self, query: ModuleReferenceQuery | str) -> CampaignContentAdvice:
        if isinstance(query, str):
            query = ModuleReferenceQuery(text=query)
        ref_result = self.module_reference.lookup(query)
        if not ref_result.found:
            advice = CampaignContentAdvice(
                query=query.text,
                found=False,
                approval_checkpoints=["Ask the DM to clarify the current module section, scene, or location."],
                recommended_next_steps=["Use a broader module/location query or select a known section heading."],
            )
            return self._with_text(advice)

        nodes = self._nodes_for_reference(query)
        relevant_nodes = self._select_relevant_nodes(query.text, nodes)
        hints = self.classify_nodes(relevant_nodes)
        if not hints:
            hints = [self._match_to_general_hint(ref_result.matches[0])]

        advice = CampaignContentAdvice(
            query=query.text,
            found=True,
            player_visible_candidates=[hint for hint in hints if self._kind(hint) == CampaignContentKind.PLAYER_VISIBLE],
            dm_only_notes=[hint for hint in hints if self._kind(hint) == CampaignContentKind.DM_SECRET],
            read_aloud_candidates=[hint for hint in hints if self._kind(hint) == CampaignContentKind.READ_ALOUD],
            encounter_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.ENCOUNTER],
            trap_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.TRAP],
            treasure_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.TREASURE],
            npc_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.NPC],
            development_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.DEVELOPMENT],
            reward_hints=[hint for hint in hints if self._kind(hint) == CampaignContentKind.REWARD],
            approval_checkpoints=self._build_approval_checkpoints(hints),
            recommended_next_steps=self._build_next_steps(hints),
        )
        return self._with_text(advice)

    def classify_nodes(self, nodes: Iterable[ModuleContentNode]) -> List[CampaignContentHint]:
        hints: List[CampaignContentHint] = []
        for node in nodes:
            hints.extend(self._classify_node(node))
        return self._dedupe_hints(hints)

    def _nodes_for_reference(self, query: ModuleReferenceQuery) -> List[ModuleContentNode]:
        nodes = self.module_reference.list_content_nodes(query.module_name)
        if nodes:
            return nodes
        # Fallback: no module filter or no nodes found. Search all nodes.
        return self.module_reference.list_content_nodes("")

    def _select_relevant_nodes(self, text: str, nodes: List[ModuleContentNode]) -> List[ModuleContentNode]:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return nodes[:20]
        selected = []
        include_descendants = False
        anchor_depth = 0
        anchor_prefix: List[str] = []
        for node in nodes:
            node_text = " ".join([node.name, node.path_text, node.text]).lower()
            if normalized in node_text:
                selected.append(node)
                include_descendants = True
                anchor_depth = node.depth
                anchor_prefix = list(node.path)
                continue
            if include_descendants and node.depth > anchor_depth and node.path[: len(anchor_prefix)] == anchor_prefix:
                selected.append(node)
                continue
            if include_descendants and node.depth <= anchor_depth:
                include_descendants = False
        return selected or nodes[:20]

    def _classify_node(self, node: ModuleContentNode) -> List[CampaignContentHint]:
        text = " ".join([node.name or "", node.node_type or "", node.text or "", self._raw_text(node.raw)]).strip()
        lower = text.lower()
        hints: List[CampaignContentHint] = []

        if self._is_read_aloud(node):
            hints.append(self._hint(CampaignContentKind.READ_ALOUD, node, confidence=0.95, automation_hint="Candidate player-facing read-aloud. DM should approve before revealing."))
            hints.append(self._hint(CampaignContentKind.PLAYER_VISIBLE, node, confidence=0.85, automation_hint="Can be displayed to players after DM approval."))

        if self._is_encounter(lower):
            hints.append(self._hint(CampaignContentKind.ENCOUNTER, node, confidence=0.82, automation_hint="Prepare encounter context. Ask DM before starting combat or applying surprise."))

        if self._is_trap(lower, node):
            hints.append(self._hint(CampaignContentKind.TRAP, node, confidence=0.88, automation_hint="Trap mechanics detected. DM approval required before resolution or state mutation."))

        if self._is_treasure(lower, node):
            hints.append(self._hint(CampaignContentKind.TREASURE, node, confidence=0.86, automation_hint="Treasure detected. Reveal/award only after DM-approved discovery."))

        if self._is_development(lower, node):
            hints.append(self._hint(CampaignContentKind.DEVELOPMENT, node, confidence=0.84, automation_hint="Branch/outcome text detected. Propose next state transition, then ask DM to approve."))

        if self._is_reward(lower, node):
            hints.append(self._hint(CampaignContentKind.REWARD, node, confidence=0.86, automation_hint="Reward/XP detected. Award only after DM-approved milestone/completion."))

        if self._is_npc(lower, node):
            hints.append(self._hint(CampaignContentKind.NPC, node, confidence=0.78, automation_hint="NPC/context reference detected. Use as DM prep or roleplay support."))

        if self._is_dm_secret(lower, node):
            hints.append(self._hint(CampaignContentKind.DM_SECRET, node, confidence=0.80, automation_hint="DM-only or hidden information likely. Do not reveal automatically."))

        if not hints and (node.name or node.text):
            hints.append(self._hint(CampaignContentKind.GENERAL, node, confidence=0.45, automation_hint="General module context. DM review recommended."))
        return hints

    def _hint(self, kind: CampaignContentKind, node: ModuleContentNode, confidence: float, automation_hint: str) -> CampaignContentHint:
        return CampaignContentHint(
            kind=kind,
            title=node.name or (node.path[-1] if node.path else "Module Content"),
            path=list(node.path),
            snippet=self._truncate(node.text or self._raw_text(node.raw)),
            requires_dm_review=kind not in {CampaignContentKind.PLAYER_VISIBLE},
            confidence=confidence,
            extracted_entities=self._extract_entities(node.text or self._raw_text(node.raw)),
            automation_hint=automation_hint,
        )

    def _match_to_general_hint(self, match) -> CampaignContentHint:
        return CampaignContentHint(
            kind=CampaignContentKind.GENERAL,
            title=match.name,
            path=list(match.path),
            snippet=self._truncate(match.snippet),
            source=match.source,
            page=match.page,
            requires_dm_review=True,
            confidence=match.score,
            extracted_entities=self._extract_entities(match.snippet),
            automation_hint=match.automation_hint or "Use as campaign context with DM approval.",
        )

    @staticmethod
    def _kind(hint: CampaignContentHint) -> CampaignContentKind:
        return hint.kind if isinstance(hint.kind, CampaignContentKind) else CampaignContentKind(str(hint.kind))

    @staticmethod
    def _is_read_aloud(node: ModuleContentNode) -> bool:
        return "readaloud" in (node.node_type or "").lower() or "read aloud" in (node.name or "").lower()

    @staticmethod
    def _is_encounter(lower: str) -> bool:
        return any(token in lower for token in ["{@creature", "attack", "combat", "initiative", "surprised", "stat block", "hiding"])

    def _is_trap(self, lower: str, node: ModuleContentNode) -> bool:
        return "trap" in lower or "snare" in lower or "pit" in lower or bool(self.DC_RE.search(lower) and self.DAMAGE_RE.search(lower))

    @staticmethod
    def _is_treasure(lower: str, node: ModuleContentNode) -> bool:
        return "treasure" in (node.name or "").lower() or any(token in lower for token in [" gp", " sp", " ep", " pp", "garnet", "belt pouch", "magic item"])

    @staticmethod
    def _is_development(lower: str, node: ModuleContentNode) -> bool:
        name = (node.name or "").lower()
        return "development" in name or "developments" in lower or any(token in lower for token in ["if the characters", "characters might", "skip ahead", "next move", "continue on", "outcome"])

    def _is_reward(self, lower: str, node: ModuleContentNode) -> bool:
        name = (node.name or "").lower()
        return "awarding experience" in name or "experience points" in lower or bool(self.XP_RE.search(lower))

    @staticmethod
    def _is_npc(lower: str, node: ModuleContentNode) -> bool:
        name = (node.name or "").lower()
        return "npc" in name or "important npcs" in lower or any(token in lower for token in ["innkeeper", "quest for the party", "townmaster", "member of the"])

    @staticmethod
    def _is_dm_secret(lower: str, node: ModuleContentNode) -> bool:
        return any(token in lower for token in ["hidden", "secret", "dm's eyes", "players aren't meant", "trap", "treasure", "ambush", "hiding"])

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        for regex in (self.CREATURE_TAG_RE, self.ITEM_TAG_RE, self.CONDITION_TAG_RE):
            entities.extend(match.group(1).strip() for match in regex.finditer(text or ""))
        for match in self.DC_RE.finditer(text or ""):
            value = match.group(1) or match.group(2)
            if value:
                entities.append(f"DC {value}")
        for match in self.DAMAGE_RE.finditer(text or ""):
            entities.append(match.group(1) or match.group(0))
        for match in self.XP_RE.finditer(text or ""):
            entities.append(f"{match.group(1)} XP")
        return sorted(set(entities), key=str.lower)

    @staticmethod
    def _raw_text(raw: dict) -> str:
        parts: List[str] = []
        for key in ("text", "summary", "desc", "entry"):
            value = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(value, str):
                parts.append(value)
        if isinstance(raw, dict):
            entries = raw.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str):
                        parts.append(entry)
                    elif isinstance(entry, dict):
                        name = entry.get("name")
                        if isinstance(name, str):
                            parts.append(name)
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _truncate(self, text: str) -> str:
        clean = " ".join(str(text or "").split())
        if len(clean) <= self.max_snippet_chars:
            return clean
        return clean[: self.max_snippet_chars - 1].rstrip() + "…"

    @staticmethod
    def _dedupe_hints(hints: List[CampaignContentHint]) -> List[CampaignContentHint]:
        seen = set()
        result = []
        for hint in hints:
            key = (str(hint.kind), hint.title.lower(), tuple(hint.path), hint.snippet)
            if key in seen:
                continue
            seen.add(key)
            result.append(hint)
        return result

    @staticmethod
    def _build_approval_checkpoints(hints: List[CampaignContentHint]) -> List[str]:
        checkpoints = []
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.ENCOUNTER for hint in hints):
            checkpoints.append("DM approval required before starting combat, applying surprise, or adding monsters to initiative.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.TRAP for hint in hints):
            checkpoints.append("DM approval required before resolving trap detection, saves, damage, or conditions.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.TREASURE for hint in hints):
            checkpoints.append("DM approval required before revealing or awarding treasure.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.DEVELOPMENT for hint in hints):
            checkpoints.append("DM approval required before applying branch outcomes or campaign state transitions.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.REWARD for hint in hints):
            checkpoints.append("DM approval required before awarding XP or milestone rewards.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.READ_ALOUD for hint in hints):
            checkpoints.append("DM should approve read-aloud text before showing it to players.")
        return checkpoints or ["DM review recommended before revealing or applying module content."]

    @staticmethod
    def _build_next_steps(hints: List[CampaignContentHint]) -> List[str]:
        steps = ["Confirm the selected module section matches the current scene."]
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.READ_ALOUD for hint in hints):
            steps.append("After approval, present the read-aloud candidate to players.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.ENCOUNTER for hint in hints):
            steps.append("Prepare encounter setup and suggested manual combat commands, but do not auto-dispatch them.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.TRAP for hint in hints):
            steps.append("Ask for perception/search intent before resolving trap mechanics.")
        if any(CampaignContentAdvisor._kind(hint) == CampaignContentKind.DEVELOPMENT for hint in hints):
            steps.append("Convert development text into candidate next-state proposals for DM approval.")
        return steps

    def _with_text(self, advice: CampaignContentAdvice) -> CampaignContentAdvice:
        return CampaignContentAdvice(
            query=advice.query,
            found=advice.found,
            player_visible_candidates=advice.player_visible_candidates,
            dm_only_notes=advice.dm_only_notes,
            read_aloud_candidates=advice.read_aloud_candidates,
            encounter_hints=advice.encounter_hints,
            trap_hints=advice.trap_hints,
            treasure_hints=advice.treasure_hints,
            npc_hints=advice.npc_hints,
            development_hints=advice.development_hints,
            reward_hints=advice.reward_hints,
            approval_checkpoints=advice.approval_checkpoints,
            recommended_next_steps=advice.recommended_next_steps,
            advisory_text=self._build_advisory_text(advice),
        )

    @staticmethod
    def _build_advisory_text(advice: CampaignContentAdvice) -> str:
        if not advice.found:
            return "\n".join([
                f"Campaign content advisory: {advice.query}",
                "No matching campaign/module content found.",
                *[f"- {item}" for item in advice.recommended_next_steps],
            ])
        lines = [f"Campaign content advisory: {advice.query}"]
        groups = [
            ("Read-aloud candidates", advice.read_aloud_candidates),
            ("Encounter hints", advice.encounter_hints),
            ("Trap hints", advice.trap_hints),
            ("Treasure hints", advice.treasure_hints),
            ("NPC hints", advice.npc_hints),
            ("Development/outcome hints", advice.development_hints),
            ("Reward hints", advice.reward_hints),
        ]
        for label, hints in groups:
            if not hints:
                continue
            lines.append(f"\n{label}:")
            for hint in hints[:3]:
                path = f" ({hint.path_text})" if hint.path_text else ""
                lines.append(f"- {hint.title}{path}: {hint.snippet}")
        lines.append("\nApproval checkpoints:")
        lines.extend(f"- {item}" for item in advice.approval_checkpoints)
        lines.append("\nRecommended next steps:")
        lines.extend(f"- {item}" for item in advice.recommended_next_steps)
        return "\n".join(lines)
