"""
SERVICES/COMPENDIUM/CAMPAIGN_TRANSITION_APPROVAL_POLICY.PY
Approval policy for campaign/sandbox/donjon state transition proposals.

G1.3 purpose:
- Classify CampaignStateTransitionProposal objects into approval categories.
- Keep the campaign runtime conservative and approval-aware.
- Define what can be auto-safe, what requires DM approval, and what must never
  be auto-applied.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- No TurnOutput dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional, Set

from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)


class CampaignTransitionApprovalCategory(str, Enum):
    """Policy result for a transition proposal."""

    AUTO_SAFE = "auto_safe"
    DM_APPROVAL_REQUIRED = "dm_approval_required"
    NEVER_AUTO = "never_auto"


@dataclass(frozen=True)
class CampaignTransitionApprovalDecision:
    """Approval policy decision for a single transition proposal."""

    proposal_id: str
    transition_type: str
    category: CampaignTransitionApprovalCategory | str
    approval_required: bool
    reason: str
    risk: str = "medium"
    blocking_reasons: List[str] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)

    @property
    def can_auto_apply(self) -> bool:
        return self.category == CampaignTransitionApprovalCategory.AUTO_SAFE and not self.approval_required

    def to_dict(self) -> Dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "transition_type": self.transition_type,
            "category": _enum_value(self.category),
            "approval_required": self.approval_required,
            "reason": self.reason,
            "risk": self.risk,
            "blocking_reasons": list(self.blocking_reasons),
            "recommended_next_steps": list(self.recommended_next_steps),
        }


@dataclass(frozen=True)
class CampaignTransitionApprovalBatchDecision:
    """Decision set for a proposal batch."""

    decisions: List[CampaignTransitionApprovalDecision] = field(default_factory=list)
    summary: str = ""

    @property
    def all_auto_safe(self) -> bool:
        return bool(self.decisions) and all(decision.can_auto_apply for decision in self.decisions)

    @property
    def requires_dm_approval(self) -> bool:
        return any(decision.category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED for decision in self.decisions)

    @property
    def has_never_auto(self) -> bool:
        return any(decision.category == CampaignTransitionApprovalCategory.NEVER_AUTO for decision in self.decisions)

    def to_dict(self) -> Dict[str, object]:
        return {
            "decisions": [decision.to_dict() for decision in self.decisions],
            "summary": self.summary,
            "all_auto_safe": self.all_auto_safe,
            "requires_dm_approval": self.requires_dm_approval,
            "has_never_auto": self.has_never_auto,
        }


class CampaignTransitionApprovalPolicy:
    """Conservative default approval policy for campaign state proposals."""

    DEFAULT_AUTO_SAFE_TYPES: Set[str] = {
        CampaignStateTransitionType.SCENE_ENTERED.value,
        CampaignStateTransitionType.ROOM_ENTERED.value,
        CampaignStateTransitionType.LOCATION_UNLOCKED.value,
    }

    DEFAULT_DM_APPROVAL_TYPES: Set[str] = {
        CampaignStateTransitionType.SCENE_COMPLETED.value,
        CampaignStateTransitionType.ROOM_COMPLETED.value,
        CampaignStateTransitionType.ENCOUNTER_SUGGESTED.value,
        CampaignStateTransitionType.ENCOUNTER_STARTED.value,
        CampaignStateTransitionType.ENCOUNTER_RESOLVED.value,
        CampaignStateTransitionType.TRAP_DETECTED.value,
        CampaignStateTransitionType.TRAP_TRIGGERED.value,
        CampaignStateTransitionType.TRAP_RESOLVED.value,
        CampaignStateTransitionType.TREASURE_DISCOVERED.value,
        CampaignStateTransitionType.TREASURE_AWARDED.value,
        CampaignStateTransitionType.XP_AWARD_CANDIDATE.value,
        CampaignStateTransitionType.MILESTONE_AWARD_CANDIDATE.value,
        CampaignStateTransitionType.NPC_INFO_REVEALED.value,
        CampaignStateTransitionType.QUEST_CLUE_DISCOVERED.value,
        CampaignStateTransitionType.QUEST_UPDATED.value,
        CampaignStateTransitionType.BRANCH_AVAILABLE.value,
        CampaignStateTransitionType.REST_SUGGESTED.value,
        CampaignStateTransitionType.DM_REVIEW_REQUIRED.value,
    }

    DEFAULT_NEVER_AUTO_TYPES: Set[str] = {
        CampaignStateTransitionType.BRANCH_SELECTED.value,
    }

    NEVER_AUTO_RISKS: Set[str] = {
        CampaignStateTransitionRisk.IRREVERSIBLE.value,
    }

    HIGH_RISK_APPROVAL_RISKS: Set[str] = {
        CampaignStateTransitionRisk.HIGH.value,
        CampaignStateTransitionRisk.IRREVERSIBLE.value,
    }

    def __init__(
        self,
        auto_safe_types: Optional[Iterable[CampaignStateTransitionType | str]] = None,
        dm_approval_types: Optional[Iterable[CampaignStateTransitionType | str]] = None,
        never_auto_types: Optional[Iterable[CampaignStateTransitionType | str]] = None,
    ) -> None:
        self.auto_safe_types = self.DEFAULT_AUTO_SAFE_TYPES if auto_safe_types is None else {_enum_value(item) for item in auto_safe_types}
        self.dm_approval_types = self.DEFAULT_DM_APPROVAL_TYPES if dm_approval_types is None else {_enum_value(item) for item in dm_approval_types}
        self.never_auto_types = self.DEFAULT_NEVER_AUTO_TYPES if never_auto_types is None else {_enum_value(item) for item in never_auto_types}

    def decide(self, proposal: CampaignStateTransitionProposal) -> CampaignTransitionApprovalDecision:
        transition_type = _enum_value(proposal.transition_type)
        risk = _enum_value(proposal.risk)
        blocking_reasons: List[str] = []

        if transition_type in self.never_auto_types:
            blocking_reasons.append("Transition type is configured as never-auto.")
        if risk in self.NEVER_AUTO_RISKS:
            blocking_reasons.append("Risk is irreversible.")
        if self._contains_state_mutation_preview(proposal):
            blocking_reasons.append("State patch preview contains mutation fields; explicit approval required.")
        if self._contains_player_harm_or_loss_tags(proposal):
            blocking_reasons.append("Proposal tags indicate loss, death, or irreversible harm; never auto-apply.")

        if blocking_reasons:
            return CampaignTransitionApprovalDecision(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                category=CampaignTransitionApprovalCategory.NEVER_AUTO,
                approval_required=True,
                reason="Proposal must not be automatically applied.",
                risk=risk,
                blocking_reasons=blocking_reasons,
                recommended_next_steps=[
                    "Ask the DM to review, revise, approve, or reject this proposal manually.",
                    "Do not mutate campaign state until explicit approval is recorded.",
                ],
            )

        if proposal.approval_required or risk in self.HIGH_RISK_APPROVAL_RISKS or transition_type in self.dm_approval_types:
            return CampaignTransitionApprovalDecision(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                category=CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED,
                approval_required=True,
                reason="Proposal requires DM approval before application.",
                risk=risk,
                recommended_next_steps=[
                    "Present the proposal to the DM with evidence and recommended next steps.",
                    "Apply only after the DM approves or revises the proposal.",
                ],
            )

        if transition_type in self.auto_safe_types and risk == CampaignStateTransitionRisk.LOW.value:
            return CampaignTransitionApprovalDecision(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                category=CampaignTransitionApprovalCategory.AUTO_SAFE,
                approval_required=False,
                reason="Low-risk bookkeeping transition is auto-safe under current policy.",
                risk=risk,
                recommended_next_steps=["May be applied by a later state-store layer if no stricter runtime policy overrides it."],
            )

        return CampaignTransitionApprovalDecision(
            proposal_id=proposal.proposal_id,
            transition_type=transition_type,
            category=CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED,
            approval_required=True,
            reason="Default conservative fallback requires DM approval.",
            risk=risk,
            recommended_next_steps=["Ask the DM to review the proposal before state mutation."],
        )

    def decide_batch(self, proposals: Iterable[CampaignStateTransitionProposal]) -> CampaignTransitionApprovalBatchDecision:
        decisions = [self.decide(proposal) for proposal in proposals]
        auto_safe = sum(1 for decision in decisions if decision.category == CampaignTransitionApprovalCategory.AUTO_SAFE)
        dm_required = sum(1 for decision in decisions if decision.category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED)
        never_auto = sum(1 for decision in decisions if decision.category == CampaignTransitionApprovalCategory.NEVER_AUTO)
        return CampaignTransitionApprovalBatchDecision(
            decisions=decisions,
            summary=(
                f"Approval policy decisions: {auto_safe} auto-safe, "
                f"{dm_required} require DM approval, {never_auto} never-auto."
            ),
        )

    @staticmethod
    def _contains_state_mutation_preview(proposal: CampaignStateTransitionProposal) -> bool:
        if not proposal.state_patch_preview:
            return False
        mutation_markers = {
            "apply_damage",
            "award_treasure",
            "award_xp",
            "branch_selected",
            "inventory_update",
            "character_state_change",
            "campaign_state_patch",
        }
        return any(key in proposal.state_patch_preview for key in mutation_markers)

    @staticmethod
    def _contains_player_harm_or_loss_tags(proposal: CampaignStateTransitionProposal) -> bool:
        tags = {str(tag).strip().lower() for tag in proposal.tags}
        dangerous = {
            "player-death",
            "permanent-loss",
            "irreversible",
            "forced-outcome",
            "character-death",
            "item-loss",
        }
        return bool(tags.intersection(dangerous))


def _enum_value(value) -> str:
    return value.value if isinstance(value, Enum) else str(value or "")
