"""
SERVICES/COMPENDIUM/CAMPAIGN_CONTENT_APPLICATION_SERVICE.PY
Application-facing service and TurnOutput mapper for CampaignContentAdvisor.

F3.4 purpose:
- Make CampaignContentAdvisor usable from campaign, sandbox, and donjon runtime.
- Convert structured CampaignContentAdvice into canonical TurnOutput.
- Separate player-safe narrative from DM-only context and approval checkpoints.
- Move toward automated campaign running while keeping explicit approval points
  for hidden information, combat starts, traps, treasure, XP, and campaign state
  transitions.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reproduce long adventure/book text.
- Does not mutate campaign state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from core.turn_output import TurnOutput
from services.compendium.campaign_content_advisor import (
    CampaignContentAdvice,
    CampaignContentAdvisor,
    CampaignContentHint,
    CampaignContentKind,
)
from services.compendium.module_reference_service import ModuleReferenceQuery


@dataclass(frozen=True)
class CampaignContentApplicationRequest:
    """Runtime/application friendly campaign content request DTO."""

    query: str = ""
    module_name: str = ""
    source: str = ""
    campaign_id: str = ""
    scene_id: str = ""
    audience: str = "dm"
    include_player_summary: bool = True
    include_read_aloud_candidate: bool = True
    include_dm_only_context: bool = True
    include_approval_checkpoints: bool = True
    max_snippet_chars: int = 360
    limit: int = 5


@dataclass(frozen=True)
class CampaignContentApplicationResult:
    """Application result before TurnOutput rendering."""

    request: CampaignContentApplicationRequest
    advice: CampaignContentAdvice
    player_safe_summary: str = ""
    dm_only_context: list[str] = field(default_factory=list)
    approval_checkpoints: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)


class CampaignContentTurnOutputMapper:
    """Maps CampaignContentApplicationResult to canonical TurnOutput."""

    def to_turn_output(self, result: CampaignContentApplicationResult) -> TurnOutput:
        return TurnOutput(
            public_narrative=self._build_public_narrative(result),
            dm_instructions=self._build_dm_instructions(result),
            suggested_commands=[],
            debug_notes=self._build_debug_notes(result),
        )

    def _build_public_narrative(self, result: CampaignContentApplicationResult) -> str:
        req = result.request
        advice = result.advice
        lines = ["🎭 **Campaign Content Advisory**"]
        if req.campaign_id:
            lines.append(f"Campaign: **{req.campaign_id}**")
        if req.scene_id:
            lines.append(f"Scene: **{req.scene_id}**")
        if req.module_name:
            lines.append(f"Module: **{req.module_name}**")
        lines.append(f"Query: **{advice.query or req.query}**")
        lines.append("")

        if not advice.found:
            lines.append("No matching campaign content was found.")
            lines.append("Ask the DM to clarify the current location, scene, or module section.")
            return "\n".join(lines)

        if req.include_player_summary:
            lines.append("Player-safe summary:")
            lines.append(result.player_safe_summary or "Relevant campaign context was found. The DM should review it before revealing details.")
            lines.append("")

        if req.include_read_aloud_candidate and advice.read_aloud_candidates:
            lines.append("Read-aloud candidate, pending DM approval:")
            lines.append(self._safe_hint_line(advice.read_aloud_candidates[0]))
            lines.append("")

        visible_categories = []
        if advice.encounter_hints:
            visible_categories.append("encounter setup")
        if advice.trap_hints:
            visible_categories.append("trap mechanics")
        if advice.treasure_hints:
            visible_categories.append("treasure")
        if advice.development_hints:
            visible_categories.append("branching outcome")
        if visible_categories:
            lines.append("DM-only content detected:")
            lines.append("- " + ", ".join(visible_categories))
            lines.append("")

        lines.append("DM approval is required before revealing hidden details or changing campaign state.")
        return "\n".join(lines)

    def _build_dm_instructions(self, result: CampaignContentApplicationResult) -> list[str]:
        req = result.request
        advice = result.advice
        instructions = [
            "This output is advisory only; it does not mutate campaign state.",
            "Review player-visible text before revealing it.",
            "Approve combat starts, trap resolution, treasure awards, XP awards, and branch outcomes before applying them.",
        ]
        if req.module_name:
            instructions.append(f"Module filter used: {req.module_name}")
        if req.source:
            instructions.append(f"Source filter used: {req.source}")
        if req.include_dm_only_context:
            instructions.extend(result.dm_only_context)
        if req.include_approval_checkpoints:
            instructions.append("Approval checkpoints:")
            instructions.extend(f"- {item}" for item in result.approval_checkpoints)
        instructions.append("Recommended next steps:")
        instructions.extend(f"- {item}" for item in result.recommended_next_steps)
        return instructions

    @staticmethod
    def _build_debug_notes(result: CampaignContentApplicationResult) -> list[str]:
        advice = result.advice
        req = result.request
        return [
            "CampaignContentAdvisor output mapped to TurnOutput.",
            f"Found: {advice.found}",
            f"Read-aloud candidates: {len(advice.read_aloud_candidates)}",
            f"Encounter hints: {len(advice.encounter_hints)}",
            f"Trap hints: {len(advice.trap_hints)}",
            f"Treasure hints: {len(advice.treasure_hints)}",
            f"Development hints: {len(advice.development_hints)}",
            f"Reward hints: {len(advice.reward_hints)}",
            f"Audience: {req.audience}",
        ]

    @staticmethod
    def _safe_hint_line(hint: CampaignContentHint) -> str:
        path = f" ({hint.path_text})" if hint.path_text else ""
        snippet = f" — {hint.snippet}" if hint.snippet else ""
        return f"- {hint.title}{path}{snippet}"


class CampaignContentApplicationService:
    """Application facade for campaign content advisory."""

    def __init__(
        self,
        advisor: CampaignContentAdvisor,
        mapper: Optional[CampaignContentTurnOutputMapper] = None,
    ) -> None:
        self.advisor = advisor
        self.mapper = mapper or CampaignContentTurnOutputMapper()

    def advise(self, request: CampaignContentApplicationRequest | ModuleReferenceQuery | Mapping[str, Any] | str) -> TurnOutput:
        app_request = self._coerce_request(request)
        query = ModuleReferenceQuery(
            text=app_request.query,
            module_name=app_request.module_name,
            source=app_request.source,
            limit=app_request.limit,
            max_snippet_chars=app_request.max_snippet_chars,
            include_dm_review_notes=True,
        )
        advice = self.advisor.advise(query)
        result = self._build_application_result(app_request, advice)
        return self.mapper.to_turn_output(result)

    def _build_application_result(
        self,
        request: CampaignContentApplicationRequest,
        advice: CampaignContentAdvice,
    ) -> CampaignContentApplicationResult:
        if not advice.found:
            return CampaignContentApplicationResult(
                request=request,
                advice=advice,
                player_safe_summary="No player-safe campaign summary is available because no matching content was found.",
                dm_only_context=["No matching module node was found for the query."],
                approval_checkpoints=advice.approval_checkpoints,
                recommended_next_steps=advice.recommended_next_steps,
            )

        return CampaignContentApplicationResult(
            request=request,
            advice=advice,
            player_safe_summary=self._build_player_safe_summary(advice),
            dm_only_context=self._build_dm_only_context(advice),
            approval_checkpoints=advice.approval_checkpoints,
            recommended_next_steps=advice.recommended_next_steps,
        )

    @staticmethod
    def _build_player_safe_summary(advice: CampaignContentAdvice) -> str:
        if advice.read_aloud_candidates:
            hint = advice.read_aloud_candidates[0]
            return f"A scene description is available for **{hint.path_text or hint.title}**, pending DM approval."
        if advice.player_visible_candidates:
            hint = advice.player_visible_candidates[0]
            return f"Player-facing context is available for **{hint.path_text or hint.title}**, pending DM approval."
        return "Relevant campaign context is available. The DM should review it before sharing details."

    @staticmethod
    def _build_dm_only_context(advice: CampaignContentAdvice) -> list[str]:
        lines: list[str] = []
        grouped = [
            ("Read-aloud", advice.read_aloud_candidates),
            ("Encounter", advice.encounter_hints),
            ("Trap", advice.trap_hints),
            ("Treasure", advice.treasure_hints),
            ("NPC", advice.npc_hints),
            ("Development", advice.development_hints),
            ("Reward", advice.reward_hints),
            ("DM-only", advice.dm_only_notes),
        ]
        for label, hints in grouped:
            if not hints:
                continue
            lines.append(f"{label} hints:")
            for hint in hints[:3]:
                path = f" ({hint.path_text})" if hint.path_text else ""
                snippet = f" — {hint.snippet}" if hint.snippet else ""
                entities = f" | entities: {', '.join(hint.extracted_entities)}" if hint.extracted_entities else ""
                lines.append(f"- {hint.title}{path}{snippet}{entities}")
        return lines

    @staticmethod
    def _coerce_request(request: CampaignContentApplicationRequest | ModuleReferenceQuery | Mapping[str, Any] | str) -> CampaignContentApplicationRequest:
        if isinstance(request, CampaignContentApplicationRequest):
            return request
        if isinstance(request, ModuleReferenceQuery):
            return CampaignContentApplicationRequest(
                query=request.text,
                module_name=request.module_name,
                source=request.source,
                limit=request.limit,
                max_snippet_chars=request.max_snippet_chars,
                include_approval_checkpoints=request.include_dm_review_notes,
            )
        if isinstance(request, str):
            return CampaignContentApplicationRequest(query=request)
        data = dict(request or {})
        return CampaignContentApplicationRequest(
            query=str(data.get("query", data.get("text", data.get("location", data.get("scene", "")))) or ""),
            module_name=str(data.get("module_name", data.get("module", "")) or ""),
            source=str(data.get("source", "") or ""),
            campaign_id=str(data.get("campaign_id", "") or ""),
            scene_id=str(data.get("scene_id", data.get("room_id", "")) or ""),
            audience=str(data.get("audience", "dm") or "dm"),
            include_player_summary=bool(data.get("include_player_summary", True)),
            include_read_aloud_candidate=bool(data.get("include_read_aloud_candidate", True)),
            include_dm_only_context=bool(data.get("include_dm_only_context", True)),
            include_approval_checkpoints=bool(data.get("include_approval_checkpoints", True)),
            max_snippet_chars=int(data.get("max_snippet_chars", 360) or 360),
            limit=int(data.get("limit", 5) or 5),
        )
