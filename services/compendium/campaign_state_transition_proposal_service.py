"""
SERVICES/COMPENDIUM/CAMPAIGN_STATE_TRANSITION_PROPOSAL_SERVICE.PY
Builds advisory campaign/sandbox/donjon state transition proposals from F3
CampaignContentAdvice.

G1.2 purpose:
- Convert CampaignContentAdvice into CampaignStateTransitionProposalResult.
- Keep all outputs proposal-only and approval-aware.
- Support campaign/module, sandbox, donjon, and combat-progression use cases.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- No TurnOutput dependency. Application/TurnOutput mapping belongs to a later G1 step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from services.compendium.campaign_content_advisor import (
    CampaignContentAdvice,
    CampaignContentHint,
    CampaignContentKind,
)
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionEvidence,
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionSource,
    CampaignStateTransitionType,
    build_proposal_id,
    proposal_requires_approval,
)


@dataclass(frozen=True)
class CampaignStateTransitionProposalRequest:
    """Input DTO for proposal generation.

    `party_action_summary` is intentionally free text. G1.2 does not interpret it
    with LLM logic; it is preserved as evidence/metadata for the DM approval step.
    """

    campaign_id: str
    scene_id: str
    advice: CampaignContentAdvice
    party_action_summary: str = ""
    source: CampaignStateTransitionSource | str = CampaignStateTransitionSource.MODULE_CONTENT
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CampaignStateTransitionProposalService:
    """Maps campaign content hints to approval-aware state transition proposals."""

    def propose(
        self,
        request: CampaignStateTransitionProposalRequest,
    ) -> CampaignStateTransitionProposalResult:
        proposals: List[CampaignStateTransitionProposal] = []
        advice = request.advice

        if not advice.found:
            proposals.append(self._dm_review_required(request, "No campaign content was found for transition inference."))
        else:
            proposals.extend(self._from_encounter_hints(request, advice.encounter_hints))
            proposals.extend(self._from_trap_hints(request, advice.trap_hints))
            proposals.extend(self._from_treasure_hints(request, advice.treasure_hints))
            proposals.extend(self._from_reward_hints(request, advice.reward_hints))
            proposals.extend(self._from_development_hints(request, advice.development_hints))
            proposals.extend(self._from_npc_hints(request, advice.npc_hints))
            proposals.extend(self._from_read_aloud_hints(request, advice.read_aloud_candidates))

        proposals = self._dedupe(proposals)
        if not proposals:
            proposals.append(self._dm_review_required(request, "Campaign content was found, but no transition-specific hints were classified."))

        return CampaignStateTransitionProposalResult(
            campaign_id=request.campaign_id,
            scene_id=request.scene_id,
            proposals=proposals,
            summary=f"Generated {len(proposals)} campaign state transition proposal(s).",
            approval_required=any(proposal.requires_human_review for proposal in proposals),
            metadata={
                "party_action_summary": request.party_action_summary,
                "source": self._source_value(request.source),
                **dict(request.metadata),
            },
        )

    def _from_encounter_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.ENCOUNTER_SUGGESTED,
            title=f"Encounter candidate: {hint.title}",
            summary="Campaign content indicates that an encounter/combat setup may be relevant.",
            risk=CampaignStateTransitionRisk.HIGH,
            next_steps=[
                "Ask the DM whether to start or prepare combat.",
                "If approved, generate visible advisory commands for initiative setup, but do not auto-dispatch them.",
                "Confirm surprise, monster placement, and player visibility before applying combat state.",
            ],
            state_patch_preview={"encounter_candidate": True, "source_path": hint.path_text},
        ) for hint in hints]

    def _from_trap_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.TRAP_DETECTED,
            title=f"Trap resolution candidate: {hint.title}",
            summary="Campaign content indicates trap mechanics or trap detection/resolution may be relevant.",
            risk=CampaignStateTransitionRisk.HIGH,
            next_steps=[
                "Ask whether characters are searching, moving cautiously, or triggering the area.",
                "DM must approve detection checks, saving throws, damage, and conditions before state is changed.",
            ],
            state_patch_preview={"trap_candidate": True, "entities": list(hint.extracted_entities)},
        ) for hint in hints]

    def _from_treasure_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.TREASURE_DISCOVERED,
            title=f"Treasure discovery candidate: {hint.title}",
            summary="Campaign content indicates treasure or loot may be discoverable.",
            risk=CampaignStateTransitionRisk.HIGH,
            next_steps=[
                "Ask the DM whether the treasure is visible, hidden, or requires a search/check.",
                "Do not award treasure or update inventory until approved.",
            ],
            state_patch_preview={"treasure_candidate": True, "entities": list(hint.extracted_entities)},
        ) for hint in hints]

    def _from_reward_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.XP_AWARD_CANDIDATE,
            title=f"Reward/XP candidate: {hint.title}",
            summary="Campaign content indicates XP, milestone, or reward assignment may be available.",
            risk=CampaignStateTransitionRisk.MEDIUM,
            next_steps=[
                "Ask the DM whether the encounter, trap, or milestone condition is complete.",
                "Award XP/milestone only after approval.",
            ],
            state_patch_preview={"reward_candidate": True, "entities": list(hint.extracted_entities)},
        ) for hint in hints]

    def _from_development_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.BRANCH_AVAILABLE,
            title=f"Branch/outcome candidate: {hint.title}",
            summary="Campaign content indicates a possible branch, outcome, or next-scene transition.",
            risk=CampaignStateTransitionRisk.HIGH,
            next_steps=[
                "Ask the DM which branch applies based on player actions and current state.",
                "Do not select or apply a branch automatically.",
                "If approved, convert the branch to a later state patch.",
            ],
            state_patch_preview={"branch_candidate": True, "source_path": hint.path_text},
        ) for hint in hints]

    def _from_npc_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.NPC_INFO_REVEALED,
            title=f"NPC information candidate: {hint.title}",
            summary="Campaign content indicates NPC context or information may be relevant.",
            risk=CampaignStateTransitionRisk.MEDIUM,
            next_steps=[
                "Ask the DM whether this NPC information is known to players or still hidden.",
                "Reveal only player-safe NPC information after approval.",
            ],
            state_patch_preview={"npc_info_candidate": True, "entities": list(hint.extracted_entities)},
        ) for hint in hints]

    def _from_read_aloud_hints(
        self,
        request: CampaignStateTransitionProposalRequest,
        hints: Iterable[CampaignContentHint],
    ) -> List[CampaignStateTransitionProposal]:
        return [self._proposal(
            request=request,
            hint=hint,
            transition_type=CampaignStateTransitionType.SCENE_ENTERED,
            title=f"Read-aloud / scene entry candidate: {hint.title}",
            summary="Campaign content includes a player-facing read-aloud candidate for scene entry.",
            risk=CampaignStateTransitionRisk.MEDIUM,
            next_steps=[
                "Ask the DM to approve the read-aloud text before showing it to players.",
                "After approval, mark the scene as entered or presented in a later state layer.",
            ],
            state_patch_preview={"scene_entry_candidate": True, "read_aloud_available": True},
        ) for hint in hints]

    def _dm_review_required(
        self,
        request: CampaignStateTransitionProposalRequest,
        reason: str,
    ) -> CampaignStateTransitionProposal:
        proposal_id = build_proposal_id(
            request.campaign_id,
            request.scene_id,
            CampaignStateTransitionType.DM_REVIEW_REQUIRED,
            "DM review required",
        )
        return CampaignStateTransitionProposal(
            proposal_id=proposal_id,
            campaign_id=request.campaign_id,
            scene_id=request.scene_id,
            transition_type=CampaignStateTransitionType.DM_REVIEW_REQUIRED,
            title="DM review required",
            summary=reason,
            source=request.source,
            risk=CampaignStateTransitionRisk.MEDIUM,
            approval_required=True,
            evidence=[CampaignStateTransitionEvidence(
                source=request.source,
                summary=reason,
                confidence=0.5,
                metadata={"party_action_summary": request.party_action_summary},
            )],
            recommended_next_steps=["Ask the DM to clarify the current scene state and desired next action."],
            player_visible_summary="The DM needs to review the current scene before the campaign state can progress.",
            dm_only_notes=[reason],
            tags=[*request.tags, "dm-review"],
        )

    def _proposal(
        self,
        request: CampaignStateTransitionProposalRequest,
        hint: CampaignContentHint,
        transition_type: CampaignStateTransitionType,
        title: str,
        summary: str,
        risk: CampaignStateTransitionRisk,
        next_steps: List[str],
        state_patch_preview: Dict[str, Any],
    ) -> CampaignStateTransitionProposal:
        approval_required = proposal_requires_approval(transition_type, risk)
        evidence = CampaignStateTransitionEvidence(
            source=request.source,
            summary=f"{hint.kind}: {hint.title}",
            quote=hint.snippet,
            path=list(hint.path),
            confidence=hint.confidence,
            metadata={
                "automation_hint": hint.automation_hint,
                "extracted_entities": list(hint.extracted_entities),
                "party_action_summary": request.party_action_summary,
            },
        )
        return CampaignStateTransitionProposal(
            proposal_id=build_proposal_id(request.campaign_id, request.scene_id, transition_type, title),
            campaign_id=request.campaign_id,
            scene_id=request.scene_id,
            transition_type=transition_type,
            title=title,
            summary=summary,
            source=request.source,
            risk=risk,
            approval_required=approval_required,
            evidence=[evidence],
            recommended_next_steps=list(next_steps),
            state_patch_preview=dict(state_patch_preview),
            player_visible_summary=self._player_visible_summary(transition_type, hint),
            dm_only_notes=[hint.snippet] if hint.snippet else [],
            tags=[*request.tags, self._transition_value(transition_type), self._kind_value(hint.kind)],
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _player_visible_summary(transition_type: CampaignStateTransitionType, hint: CampaignContentHint) -> str:
        if transition_type == CampaignStateTransitionType.SCENE_ENTERED:
            return "A scene description is available, pending DM approval."
        if transition_type == CampaignStateTransitionType.ENCOUNTER_SUGGESTED:
            return "A possible encounter is present, pending DM approval."
        if transition_type == CampaignStateTransitionType.TRAP_DETECTED:
            return "The DM may need to resolve a hazard or trap."
        if transition_type == CampaignStateTransitionType.TREASURE_DISCOVERED:
            return "There may be discoverable treasure, pending DM approval."
        if transition_type == CampaignStateTransitionType.XP_AWARD_CANDIDATE:
            return "A reward or milestone may be available, pending DM approval."
        if transition_type == CampaignStateTransitionType.NPC_INFO_REVEALED:
            return "NPC information may be relevant, pending DM approval."
        return "A campaign state transition may be available, pending DM approval."

    @staticmethod
    def _dedupe(proposals: List[CampaignStateTransitionProposal]) -> List[CampaignStateTransitionProposal]:
        seen = set()
        result: List[CampaignStateTransitionProposal] = []
        for proposal in proposals:
            key = (proposal.proposal_id, proposal.transition_type, proposal.title)
            if key in seen:
                continue
            seen.add(key)
            result.append(proposal)
        return result

    @staticmethod
    def _transition_value(value: CampaignStateTransitionType | str) -> str:
        return value.value if isinstance(value, CampaignStateTransitionType) else str(value)

    @staticmethod
    def _source_value(value: CampaignStateTransitionSource | str) -> str:
        return value.value if isinstance(value, CampaignStateTransitionSource) else str(value)

    @staticmethod
    def _kind_value(value: CampaignContentKind | str) -> str:
        return value.value if isinstance(value, CampaignContentKind) else str(value)
