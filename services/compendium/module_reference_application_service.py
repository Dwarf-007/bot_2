"""
SERVICES/COMPENDIUM/MODULE_REFERENCE_APPLICATION_SERVICE.PY
Application-facing service and TurnOutput mapper for ModuleReferenceService.

F3.2 purpose:
- Make ModuleReferenceService usable from campaign, sandbox, and donjon runtime.
- Convert module/adventure/book references into canonical TurnOutput.
- Separate player-visible summary from DM-only review instructions.
- Move toward automated campaign running while allowing human/DM approval where
  hidden information, branching logic, or state-changing decisions are involved.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- Does not reveal long adventure/book text.
- Does not mutate campaign state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from core.turn_output import TurnOutput
from services.compendium.module_reference_service import (
    ModuleReferenceMatch,
    ModuleReferenceQuery,
    ModuleReferenceResult,
    ModuleReferenceService,
)


@dataclass(frozen=True)
class ModuleReferenceApplicationRequest:
    """Runtime/application friendly request DTO for module lookup."""

    query: str = ""
    module_name: str = ""
    source: str = ""
    scene_id: str = ""
    campaign_id: str = ""
    audience: str = "dm"
    include_player_summary: bool = True
    include_dm_review_notes: bool = True
    max_snippet_chars: int = 360
    limit: int = 3


@dataclass(frozen=True)
class ModuleReferenceApplicationResult:
    """Application-level result before TurnOutput rendering."""

    request: ModuleReferenceApplicationRequest
    reference_result: ModuleReferenceResult
    player_visible_summary: str = ""
    dm_only_context: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)


class ModuleReferenceTurnOutputMapper:
    """Maps module reference application results to canonical TurnOutput."""

    def to_turn_output(self, result: ModuleReferenceApplicationResult) -> TurnOutput:
        public_narrative = self._build_public_narrative(result)
        dm_instructions = self._build_dm_instructions(result)
        debug_notes = self._build_debug_notes(result)
        return TurnOutput(
            public_narrative=public_narrative,
            dm_instructions=dm_instructions,
            suggested_commands=[],
            debug_notes=debug_notes,
        )

    def _build_public_narrative(self, result: ModuleReferenceApplicationResult) -> str:
        req = result.request
        ref = result.reference_result
        lines = ["📚 **Module Reference Advisory**"]
        if req.campaign_id:
            lines.append(f"Campaign: **{req.campaign_id}**")
        if req.scene_id:
            lines.append(f"Scene: **{req.scene_id}**")
        if req.module_name:
            lines.append(f"Module: **{req.module_name}**")
        lines.append(f"Query: **{ref.query or req.query}**")
        lines.append("")

        if not ref.found:
            lines.append("No module/campaign reference was found for this query.")
            lines.append("Ask the DM for clarification or choose a broader location/section name.")
            return "\n".join(lines)

        if req.include_player_summary:
            lines.append("Player-safe summary:")
            lines.append(result.player_visible_summary or self._player_safe_summary(ref.matches[0]))
            lines.append("")
        else:
            lines.append("Reference found. Player-facing summary is disabled for this request.")
            lines.append("")

        lines.append("DM review is recommended before revealing hidden details or changing campaign state.")
        return "\n".join(lines)

    def _build_dm_instructions(self, result: ModuleReferenceApplicationResult) -> list[str]:
        ref = result.reference_result
        req = result.request
        instructions = [
            "This output is advisory only; it does not mutate campaign state.",
            "Review hidden information before sharing anything with players.",
            "Approve any state-changing next step before applying it to the campaign runtime.",
        ]
        if req.module_name:
            instructions.append(f"Module filter used: {req.module_name}")
        if req.source:
            instructions.append(f"Source filter used: {req.source}")
        if ref.found:
            primary = ref.matches[0]
            instructions.append(f"Primary reference: {primary.name} | path: {primary.path_text or primary.name} | source: {primary.source}")
            if primary.automation_hint:
                instructions.append(f"Automation hint: {primary.automation_hint}")
            if primary.snippet:
                instructions.append(f"DM-only reference snippet: {primary.snippet}")
        instructions.extend(result.dm_only_context)
        instructions.extend(result.recommended_next_steps)
        return instructions

    @staticmethod
    def _build_debug_notes(result: ModuleReferenceApplicationResult) -> list[str]:
        ref = result.reference_result
        req = result.request
        return [
            "ModuleReferenceApplicationService output mapped to TurnOutput.",
            f"Found: {ref.found}",
            f"Matches: {len(ref.matches)}",
            f"DM review recommended: {ref.dm_review_recommended}",
            f"Audience: {req.audience}",
        ]

    @staticmethod
    def _player_safe_summary(match: ModuleReferenceMatch) -> str:
        path = f" ({match.path_text})" if match.path_text else ""
        source = f" [{match.source}]" if match.source else ""
        return f"Relevant campaign reference found: {match.name}{path}{source}. The DM has additional context to review."


class ModuleReferenceApplicationService:
    """Application facade for campaign/module reference lookup."""

    def __init__(
        self,
        module_reference: ModuleReferenceService,
        mapper: Optional[ModuleReferenceTurnOutputMapper] = None,
    ) -> None:
        self.module_reference = module_reference
        self.mapper = mapper or ModuleReferenceTurnOutputMapper()

    def advise(self, request: ModuleReferenceApplicationRequest | ModuleReferenceQuery | Mapping[str, Any] | str) -> TurnOutput:
        app_request = self._coerce_request(request)
        ref_query = ModuleReferenceQuery(
            text=app_request.query,
            module_name=app_request.module_name,
            source=app_request.source,
            limit=app_request.limit,
            max_snippet_chars=app_request.max_snippet_chars,
            include_dm_review_notes=app_request.include_dm_review_notes,
        )
        reference_result = self.module_reference.lookup(ref_query)
        application_result = self._build_application_result(app_request, reference_result)
        return self.mapper.to_turn_output(application_result)

    def _build_application_result(
        self,
        request: ModuleReferenceApplicationRequest,
        reference_result: ModuleReferenceResult,
    ) -> ModuleReferenceApplicationResult:
        if not reference_result.found:
            return ModuleReferenceApplicationResult(
                request=request,
                reference_result=reference_result,
                player_visible_summary="No player-visible summary is available because no reference was found.",
                dm_only_context=["Consider broadening the query or selecting a known module section/location."],
                recommended_next_steps=["Ask the DM to clarify the current module location or scene objective."],
            )

        primary = reference_result.matches[0]
        player_summary = self._build_player_visible_summary(primary)
        dm_context = self._build_dm_context(primary)
        next_steps = self._build_next_steps(primary, request)
        return ModuleReferenceApplicationResult(
            request=request,
            reference_result=reference_result,
            player_visible_summary=player_summary,
            dm_only_context=dm_context,
            recommended_next_steps=next_steps,
        )

    @staticmethod
    def _build_player_visible_summary(match: ModuleReferenceMatch) -> str:
        # Keep this deliberately short and non-revealing. Full/hidden details go
        # to dm_instructions for human approval.
        location = match.path_text or match.name
        return f"The current scene appears to connect to **{location}**. The DM should review the module context before revealing details."

    @staticmethod
    def _build_dm_context(match: ModuleReferenceMatch) -> list[str]:
        context = []
        if match.snippet:
            context.append(f"Reference snippet: {match.snippet}")
        if match.path_text:
            context.append(f"Reference path: {match.path_text}")
        if match.requires_dm_review:
            context.append("DM approval required before exposing hidden information or applying state changes.")
        return context

    @staticmethod
    def _build_next_steps(match: ModuleReferenceMatch, request: ModuleReferenceApplicationRequest) -> list[str]:
        steps = [
            "Confirm whether this reference matches the current player-facing scene.",
            "If the section contains read-aloud text, decide what can be safely presented to players.",
            "If the section implies combat, trap, treasure, or branching outcome, ask for DM approval before mutating campaign state.",
        ]
        if request.include_player_summary:
            steps.append("After approval, render only player-safe summary or read-aloud material.")
        if match.automation_hint:
            steps.append(f"Automation hint: {match.automation_hint}")
        return steps

    @staticmethod
    def _coerce_request(request: ModuleReferenceApplicationRequest | ModuleReferenceQuery | Mapping[str, Any] | str) -> ModuleReferenceApplicationRequest:
        if isinstance(request, ModuleReferenceApplicationRequest):
            return request
        if isinstance(request, ModuleReferenceQuery):
            return ModuleReferenceApplicationRequest(
                query=request.text,
                module_name=request.module_name,
                source=request.source,
                limit=request.limit,
                max_snippet_chars=request.max_snippet_chars,
                include_dm_review_notes=request.include_dm_review_notes,
            )
        if isinstance(request, str):
            return ModuleReferenceApplicationRequest(query=request)
        data = dict(request or {})
        return ModuleReferenceApplicationRequest(
            query=str(data.get("query", data.get("text", data.get("location", ""))) or ""),
            module_name=str(data.get("module_name", data.get("module", "")) or ""),
            source=str(data.get("source", "") or ""),
            scene_id=str(data.get("scene_id", data.get("room_id", "")) or ""),
            campaign_id=str(data.get("campaign_id", "") or ""),
            audience=str(data.get("audience", "dm") or "dm"),
            include_player_summary=bool(data.get("include_player_summary", True)),
            include_dm_review_notes=bool(data.get("include_dm_review_notes", True)),
            max_snippet_chars=int(data.get("max_snippet_chars", 360) or 360),
            limit=int(data.get("limit", 3) or 3),
        )
