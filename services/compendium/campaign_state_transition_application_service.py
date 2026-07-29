"""
SERVICES/COMPENDIUM/CAMPAIGN_STATE_TRANSITION_APPLICATION_SERVICE.PY
Application-facing service and TurnOutput mapper for G1 campaign state transition proposals.

G1.4 purpose:
- Make G1.2 transition proposals and G1.3 approval decisions usable from runtime.
- Convert proposal batches into canonical TurnOutput for DM-facing review.
- Keep all output advisory-only and approval-aware.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- No automatic state application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from core.turn_output import TurnOutput
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
)
from services.compendium.campaign_state_transition_proposal_service import (
    CampaignStateTransitionProposalRequest,
    CampaignStateTransitionProposalService,
)
from services.compendium.campaign_transition_approval_policy import (
    CampaignTransitionApprovalBatchDecision,
    CampaignTransitionApprovalCategory,
    CampaignTransitionApprovalDecision,
    CampaignTransitionApprovalPolicy,
)


@dataclass(frozen=True)
class CampaignStateTransitionApplicationRequest:
    """Runtime/application request DTO for transition proposal rendering."""

    campaign_id: str = ""
    scene_id: str = ""
    proposal_request: Optional[CampaignStateTransitionProposalRequest] = None
    proposal_result: Optional[CampaignStateTransitionProposalResult] = None
    audience: str = "dm"
    include_player_summary: bool = True
    include_dm_only_notes: bool = True
    include_evidence: bool = True
    include_state_patch_preview: bool = True
    include_approval_decisions: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CampaignStateTransitionApplicationResult:
    """Application-level result before TurnOutput rendering."""

    request: CampaignStateTransitionApplicationRequest
    proposal_result: CampaignStateTransitionProposalResult
    approval_decisions: CampaignTransitionApprovalBatchDecision
    player_safe_summary: str = ""
    dm_review_summary: str = ""


class CampaignStateTransitionTurnOutputMapper:
    """Maps transition proposals and approval decisions to canonical TurnOutput."""

    def to_turn_output(self, result: CampaignStateTransitionApplicationResult) -> TurnOutput:
        return TurnOutput(
            public_narrative=self._build_public_narrative(result),
            dm_instructions=self._build_dm_instructions(result),
            suggested_commands=[],
            debug_notes=self._build_debug_notes(result),
        )

    def _build_public_narrative(self, result: CampaignStateTransitionApplicationResult) -> str:
        req = result.request
        proposals = result.proposal_result.proposals
        decisions = result.approval_decisions.decisions
        lines = ["🧭 **Campaign State Transition Advisory**"]
        if result.proposal_result.campaign_id or req.campaign_id:
            lines.append(f"Campaign: **{result.proposal_result.campaign_id or req.campaign_id}**")
        if result.proposal_result.scene_id or req.scene_id:
            lines.append(f"Scene: **{result.proposal_result.scene_id or req.scene_id}**")
        lines.append("")

        if not proposals:
            lines.append("No state transition proposals were generated.")
            lines.append("Ask the DM to clarify current scene state and desired next action.")
            return "\n".join(lines)

        if req.include_player_summary:
            lines.append("Player-safe summary:")
            lines.append(result.player_safe_summary or self._player_safe_summary(proposals, decisions))
            lines.append("")

        lines.append("Transition proposals pending review:")
        for proposal in proposals[:5]:
            lines.append(f"- **{proposal.title}**: {proposal.player_visible_summary or proposal.summary}")
        if len(proposals) > 5:
            lines.append(f"- ...and {len(proposals) - 5} more proposal(s).")
        lines.append("")

        if result.approval_decisions.has_never_auto:
            lines.append("⚠️ Some proposals are **never-auto** and must not be applied without explicit DM handling.")
        elif result.approval_decisions.requires_dm_approval:
            lines.append("DM approval is required before applying any state-changing proposal.")
        elif result.approval_decisions.all_auto_safe:
            lines.append("All proposals are low-risk bookkeeping transitions under the current policy.")
        else:
            lines.append("Review the DM instructions before applying any campaign state changes.")

        return "\n".join(lines)

    def _build_dm_instructions(self, result: CampaignStateTransitionApplicationResult) -> list[str]:
        req = result.request
        instructions = [
            "This output is advisory only; it does not mutate campaign state.",
            "Apply proposals only through a later approved state-store/runtime layer.",
            "Review evidence, risk, approval category, and state patch previews before approving.",
        ]

        if req.include_approval_decisions:
            instructions.append("Approval policy summary:")
            instructions.append(result.approval_decisions.summary)

        for proposal in result.proposal_result.proposals:
            decision = self._decision_for(result.approval_decisions.decisions, proposal.proposal_id)
            instructions.append("")
            instructions.append(f"Proposal: {proposal.title}")
            instructions.append(f"- ID: {proposal.proposal_id}")
            instructions.append(f"- Type: {self._value(proposal.transition_type)}")
            instructions.append(f"- Risk: {self._value(proposal.risk)}")
            instructions.append(f"- Summary: {proposal.summary}")
            if decision:
                instructions.append(f"- Approval category: {self._value(decision.category)}")
                instructions.append(f"- Approval reason: {decision.reason}")
                if decision.blocking_reasons:
                    instructions.append("- Blocking reasons:")
                    instructions.extend(f"  - {reason}" for reason in decision.blocking_reasons)
            if req.include_evidence and proposal.evidence:
                instructions.append("- Evidence:")
                for evidence in proposal.evidence[:3]:
                    quote = f" | quote: {evidence.quote}" if evidence.quote else ""
                    path = f" | path: {evidence.path_text}" if evidence.path_text else ""
                    instructions.append(f"  - {evidence.summary} (confidence {evidence.confidence:.2f}){path}{quote}")
            if req.include_state_patch_preview and proposal.state_patch_preview:
                instructions.append(f"- State patch preview: {proposal.state_patch_preview}")
            if req.include_dm_only_notes and proposal.dm_only_notes:
                instructions.append("- DM-only notes:")
                instructions.extend(f"  - {note}" for note in proposal.dm_only_notes[:3])
            if proposal.recommended_next_steps:
                instructions.append("- Recommended next steps:")
                instructions.extend(f"  - {step}" for step in proposal.recommended_next_steps)

        return instructions

    @staticmethod
    def _build_debug_notes(result: CampaignStateTransitionApplicationResult) -> list[str]:
        return [
            "CampaignStateTransitionApplicationService output mapped to TurnOutput.",
            f"Proposals: {len(result.proposal_result.proposals)}",
            f"Approval decisions: {len(result.approval_decisions.decisions)}",
            f"Requires DM approval: {result.approval_decisions.requires_dm_approval}",
            f"Has never-auto: {result.approval_decisions.has_never_auto}",
            f"Audience: {result.request.audience}",
        ]

    @staticmethod
    def _player_safe_summary(
        proposals: list[CampaignStateTransitionProposal],
        decisions: list[CampaignTransitionApprovalDecision],
    ) -> str:
        if not proposals:
            return "No campaign state transition is currently proposed."
        never_auto = any(decision.category == CampaignTransitionApprovalCategory.NEVER_AUTO for decision in decisions)
        dm_required = any(decision.category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED for decision in decisions)
        if never_auto:
            return "Possible campaign progression was identified, but some options require explicit DM handling."
        if dm_required:
            return "Possible campaign progression was identified. The DM must approve the next state change."
        return "Low-risk campaign bookkeeping proposals are available."

    @staticmethod
    def _decision_for(
        decisions: list[CampaignTransitionApprovalDecision],
        proposal_id: str,
    ) -> Optional[CampaignTransitionApprovalDecision]:
        for decision in decisions:
            if decision.proposal_id == proposal_id:
                return decision
        return None

    @staticmethod
    def _value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)


class CampaignStateTransitionApplicationService:
    """Application facade for G1 transition proposal rendering."""

    def __init__(
        self,
        proposal_service: Optional[CampaignStateTransitionProposalService] = None,
        approval_policy: Optional[CampaignTransitionApprovalPolicy] = None,
        mapper: Optional[CampaignStateTransitionTurnOutputMapper] = None,
    ) -> None:
        self.proposal_service = proposal_service or CampaignStateTransitionProposalService()
        self.approval_policy = approval_policy or CampaignTransitionApprovalPolicy()
        self.mapper = mapper or CampaignStateTransitionTurnOutputMapper()

    def advise(
        self,
        request: CampaignStateTransitionApplicationRequest | CampaignStateTransitionProposalRequest | CampaignStateTransitionProposalResult | Mapping[str, Any],
    ) -> TurnOutput:
        app_request = self._coerce_request(request)
        proposal_result = self._resolve_proposal_result(app_request)
        approval_decisions = self.approval_policy.decide_batch(proposal_result.proposals)
        application_result = CampaignStateTransitionApplicationResult(
            request=app_request,
            proposal_result=proposal_result,
            approval_decisions=approval_decisions,
            player_safe_summary=self.mapper._player_safe_summary(proposal_result.proposals, approval_decisions.decisions),
            dm_review_summary=approval_decisions.summary,
        )
        return self.mapper.to_turn_output(application_result)

    def build_application_result(
        self,
        request: CampaignStateTransitionApplicationRequest | CampaignStateTransitionProposalRequest | CampaignStateTransitionProposalResult | Mapping[str, Any],
    ) -> CampaignStateTransitionApplicationResult:
        app_request = self._coerce_request(request)
        proposal_result = self._resolve_proposal_result(app_request)
        approval_decisions = self.approval_policy.decide_batch(proposal_result.proposals)
        return CampaignStateTransitionApplicationResult(
            request=app_request,
            proposal_result=proposal_result,
            approval_decisions=approval_decisions,
            player_safe_summary=self.mapper._player_safe_summary(proposal_result.proposals, approval_decisions.decisions),
            dm_review_summary=approval_decisions.summary,
        )

    def _resolve_proposal_result(self, request: CampaignStateTransitionApplicationRequest) -> CampaignStateTransitionProposalResult:
        if request.proposal_result is not None:
            return request.proposal_result
        if request.proposal_request is not None:
            return self.proposal_service.propose(request.proposal_request)
        return CampaignStateTransitionProposalResult(
            campaign_id=request.campaign_id,
            scene_id=request.scene_id,
            proposals=[],
            summary="No proposal request or proposal result was supplied.",
            approval_required=True,
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _coerce_request(
        request: CampaignStateTransitionApplicationRequest | CampaignStateTransitionProposalRequest | CampaignStateTransitionProposalResult | Mapping[str, Any],
    ) -> CampaignStateTransitionApplicationRequest:
        if isinstance(request, CampaignStateTransitionApplicationRequest):
            return request
        if isinstance(request, CampaignStateTransitionProposalRequest):
            return CampaignStateTransitionApplicationRequest(
                campaign_id=request.campaign_id,
                scene_id=request.scene_id,
                proposal_request=request,
                metadata=dict(request.metadata),
            )
        if isinstance(request, CampaignStateTransitionProposalResult):
            return CampaignStateTransitionApplicationRequest(
                campaign_id=request.campaign_id,
                scene_id=request.scene_id,
                proposal_result=request,
                metadata=dict(request.metadata),
            )
        data = dict(request or {})
        proposal_result = data.get("proposal_result")
        proposal_request = data.get("proposal_request")
        return CampaignStateTransitionApplicationRequest(
            campaign_id=str(data.get("campaign_id", "")),
            scene_id=str(data.get("scene_id", "")),
            proposal_request=proposal_request if isinstance(proposal_request, CampaignStateTransitionProposalRequest) else None,
            proposal_result=proposal_result if isinstance(proposal_result, CampaignStateTransitionProposalResult) else None,
            audience=str(data.get("audience", "dm") or "dm"),
            include_player_summary=bool(data.get("include_player_summary", True)),
            include_dm_only_notes=bool(data.get("include_dm_only_notes", True)),
            include_evidence=bool(data.get("include_evidence", True)),
            include_state_patch_preview=bool(data.get("include_state_patch_preview", True)),
            include_approval_decisions=bool(data.get("include_approval_decisions", True)),
            metadata=dict(data.get("metadata", {})),
        )
