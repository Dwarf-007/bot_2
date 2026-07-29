"""
SERVICES/COMPENDIUM/CHARACTER_CREATION_APPLICATION_SERVICE.PY
Application-facing service and TurnOutput mapper for CharacterCreationAdvisor.

F2.3 purpose:
- Make CharacterCreationAdvisor usable from sandbox/donjon/application runtime.
- Convert CharacterCreationAdvice into the canonical TurnOutput contract.
- Keep the feature advisory-only and free of Discord/Avrae coupling.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No D&D Beyond integration.
- No LLM calls.
- No database dependency.
- Does not mutate character sheets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from core.turn_output import TurnOutput
from services.compendium.character_creation_advisor import (
    CharacterBuildRole,
    CharacterCreationAdvice,
    CharacterCreationAdvisor,
    CharacterCreationChecklistItem,
    CharacterCreationRequest,
)


@dataclass(frozen=True)
class CharacterCreationApplicationRequest:
    """Application/runtime friendly request DTO.

    This intentionally mirrors CharacterCreationRequest while avoiding direct
    UI/Discord concepts. It can be built from command payloads, sandbox runtime
    intents, donjon prep workflows, or tests.
    """

    concept: str = ""
    starting_level: int = 1
    selected_class: str = ""
    selected_species: str = ""
    selected_background: str = ""
    selected_feat: str = ""
    preferred_role: CharacterBuildRole | str = CharacterBuildRole.UNKNOWN
    ability_score_method: str = ""
    include_spell_review: bool = True
    include_donjon_readiness: bool = False
    include_sandbox_readiness: bool = False
    audience: str = "player"
    channel_id: str = ""
    requester_id: str = ""


class CharacterCreationTurnOutputMapper:
    """Maps CharacterCreationAdvice to canonical TurnOutput."""

    def to_turn_output(self, advice: CharacterCreationAdvice, request: CharacterCreationApplicationRequest | None = None) -> TurnOutput:
        public_narrative = self._build_public_narrative(advice)
        dm_instructions = self._build_dm_instructions(advice, request=request)
        debug_notes = self._build_debug_notes(advice, request=request)
        return TurnOutput(
            public_narrative=public_narrative,
            dm_instructions=dm_instructions,
            suggested_commands=[],
            debug_notes=debug_notes,
        )

    def _build_public_narrative(self, advice: CharacterCreationAdvice) -> str:
        concept = f" — {advice.concept}" if advice.concept else ""
        lines = [
            f"🧭 **Character Creation Advisory{concept}**",
            f"Starting level: **{advice.starting_level}**",
            f"Preferred role: **{advice.preferred_role}**",
        ]

        selected = []
        if advice.selected_class:
            selected.append(f"Class: **{advice.selected_class}**")
        if advice.selected_species:
            selected.append(f"Species: **{advice.selected_species}**")
        if advice.selected_background:
            selected.append(f"Background: **{advice.selected_background}**")
        if advice.selected_feat:
            selected.append(f"Feat: **{advice.selected_feat}**")
        if selected:
            lines.append("")
            lines.append("Selected options:")
            lines.extend(f"- {item}" for item in selected)

        if advice.missing_choices:
            lines.append("")
            lines.append("Missing required decisions:")
            lines.extend(f"- {choice}" for choice in advice.missing_choices)

        required_items = [item for item in advice.checklist if item.required]
        optional_items = [item for item in advice.checklist if not item.required]
        if required_items:
            lines.append("")
            lines.append("Required checklist:")
            lines.extend(self._format_items(required_items, limit=8))
        if optional_items:
            lines.append("")
            lines.append("Advisory checklist:")
            lines.extend(self._format_items(optional_items, limit=10))

        lines.append("")
        lines.append("_This is advisory guidance. The DM/player should finalize and record the character sheet in the chosen sheet tool._")
        return "\n".join(lines)

    @staticmethod
    def _format_items(items: List[CharacterCreationChecklistItem], limit: int) -> List[str]:
        rows = []
        for item in items[:limit]:
            detail = f" — {item.detail}" if item.detail else ""
            rows.append(f"- {item.label}{detail}")
        if len(items) > limit:
            rows.append(f"- ...and {len(items) - limit} more item(s).")
        return rows

    @staticmethod
    def _build_dm_instructions(advice: CharacterCreationAdvice, request: CharacterCreationApplicationRequest | None = None) -> List[str]:
        instructions = [
            "This output is advisory only; it does not create or mutate a character sheet.",
            "The DM/player should confirm allowed sources, rules version, and campaign-specific restrictions.",
            "Record the final character in Avrae, D&D Beyond, a VTT, or the selected sheet tool manually.",
        ]
        if advice.missing_choices:
            instructions.append("Resolve missing required decisions before considering the character ready for play.")
        if request and request.include_donjon_readiness:
            instructions.append("For donjon/megadungeon play, verify party role coverage and dungeon-readiness items.")
        if request and request.include_sandbox_readiness:
            instructions.append("For sandbox play, verify character hooks, goals, relationships, and non-combat utility.")
        return instructions

    @staticmethod
    def _build_debug_notes(advice: CharacterCreationAdvice, request: CharacterCreationApplicationRequest | None = None) -> List[str]:
        notes = [
            "CharacterCreationAdvisor output mapped to TurnOutput.",
            f"Checklist items: {len(advice.checklist)}",
            f"Missing choices: {len(advice.missing_choices)}",
            f"Lookups: {len(advice.lookups)}",
        ]
        if request:
            notes.append(f"Audience: {request.audience}")
            if request.channel_id:
                notes.append(f"Channel ID: {request.channel_id}")
            if request.requester_id:
                notes.append(f"Requester ID: {request.requester_id}")
        return notes


class CharacterCreationApplicationService:
    """Application facade for character creation advisory."""

    def __init__(
        self,
        advisor: CharacterCreationAdvisor,
        mapper: Optional[CharacterCreationTurnOutputMapper] = None,
    ) -> None:
        self.advisor = advisor
        self.mapper = mapper or CharacterCreationTurnOutputMapper()

    def advise(self, request: CharacterCreationApplicationRequest | CharacterCreationRequest | Mapping[str, Any]) -> TurnOutput:
        app_request = self._coerce_request(request)
        advisor_request = self._to_advisor_request(app_request)
        advice = self.advisor.build_advice(advisor_request)
        return self.mapper.to_turn_output(advice, request=app_request)

    @staticmethod
    def _to_advisor_request(request: CharacterCreationApplicationRequest) -> CharacterCreationRequest:
        return CharacterCreationRequest(
            concept=request.concept,
            starting_level=request.starting_level,
            selected_class=request.selected_class,
            selected_species=request.selected_species,
            selected_background=request.selected_background,
            selected_feat=request.selected_feat,
            preferred_role=request.preferred_role,
            ability_score_method=request.ability_score_method,
            include_spell_review=request.include_spell_review,
            include_donjon_readiness=request.include_donjon_readiness,
            include_sandbox_readiness=request.include_sandbox_readiness,
        )

    @staticmethod
    def _coerce_request(request: CharacterCreationApplicationRequest | CharacterCreationRequest | Mapping[str, Any]) -> CharacterCreationApplicationRequest:
        if isinstance(request, CharacterCreationApplicationRequest):
            return request
        if isinstance(request, CharacterCreationRequest):
            return CharacterCreationApplicationRequest(
                concept=request.concept,
                starting_level=request.starting_level,
                selected_class=request.selected_class,
                selected_species=request.selected_species,
                selected_background=request.selected_background,
                selected_feat=request.selected_feat,
                preferred_role=request.preferred_role,
                ability_score_method=request.ability_score_method,
                include_spell_review=request.include_spell_review,
                include_donjon_readiness=request.include_donjon_readiness,
                include_sandbox_readiness=request.include_sandbox_readiness,
            )
        data = dict(request or {})
        return CharacterCreationApplicationRequest(
            concept=str(data.get("concept", "")),
            starting_level=int(data.get("starting_level", data.get("level", 1)) or 1),
            selected_class=str(data.get("selected_class", data.get("class", "")) or ""),
            selected_species=str(data.get("selected_species", data.get("species", data.get("race", ""))) or ""),
            selected_background=str(data.get("selected_background", data.get("background", "")) or ""),
            selected_feat=str(data.get("selected_feat", data.get("feat", "")) or ""),
            preferred_role=data.get("preferred_role", data.get("role", CharacterBuildRole.UNKNOWN)),
            ability_score_method=str(data.get("ability_score_method", "") or ""),
            include_spell_review=bool(data.get("include_spell_review", True)),
            include_donjon_readiness=bool(data.get("include_donjon_readiness", False)),
            include_sandbox_readiness=bool(data.get("include_sandbox_readiness", False)),
            audience=str(data.get("audience", "player") or "player"),
            channel_id=str(data.get("channel_id", "") or ""),
            requester_id=str(data.get("requester_id", "") or ""),
        )
