"""
SERVICES/COMPENDIUM/CAMPAIGN_STATE_TRANSITION_MODELS.PY
Canonical advisory models for campaign/sandbox/donjon state transition proposals.

G1.1 purpose:
- Define shared transition proposal models used by Campaign, Sandbox, and Donjon runtime.
- Represent possible state changes without mutating campaign state.
- Preserve evidence, risk, approval, and recommended next-step metadata.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No database dependency.
- No campaign state mutation.
- Proposal-only: applying a proposal belongs to a later approved state-store/runtime layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional


class CampaignStateTransitionType(str, Enum):
    """Canonical transition categories shared by campaign, sandbox, and donjon mode."""

    SCENE_ENTERED = "scene_entered"
    SCENE_COMPLETED = "scene_completed"

    ROOM_ENTERED = "room_entered"
    ROOM_COMPLETED = "room_completed"
    LOCATION_UNLOCKED = "location_unlocked"

    ENCOUNTER_SUGGESTED = "encounter_suggested"
    ENCOUNTER_STARTED = "encounter_started"
    ENCOUNTER_RESOLVED = "encounter_resolved"

    TRAP_DETECTED = "trap_detected"
    TRAP_TRIGGERED = "trap_triggered"
    TRAP_RESOLVED = "trap_resolved"

    TREASURE_DISCOVERED = "treasure_discovered"
    TREASURE_AWARDED = "treasure_awarded"

    XP_AWARD_CANDIDATE = "xp_award_candidate"
    MILESTONE_AWARD_CANDIDATE = "milestone_award_candidate"

    NPC_INFO_REVEALED = "npc_info_revealed"
    QUEST_CLUE_DISCOVERED = "quest_clue_discovered"
    QUEST_UPDATED = "quest_updated"

    BRANCH_AVAILABLE = "branch_available"
    BRANCH_SELECTED = "branch_selected"

    REST_SUGGESTED = "rest_suggested"
    DM_REVIEW_REQUIRED = "dm_review_required"


class CampaignStateTransitionRisk(str, Enum):
    """Risk profile used to decide whether a proposal can ever be auto-applied."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IRREVERSIBLE = "irreversible"


class CampaignStateTransitionApprovalStatus(str, Enum):
    """Approval lifecycle for transition proposals."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    APPLIED = "applied"


class CampaignStateTransitionSource(str, Enum):
    """High-level source of the proposed transition."""

    MODULE_CONTENT = "module_content"
    DONJON_RUNTIME = "donjon_runtime"
    SANDBOX_RUNTIME = "sandbox_runtime"
    COMBAT_RUNTIME = "combat_runtime"
    DM_INPUT = "dm_input"
    PLAYER_ACTION = "player_action"
    SYSTEM_INFERENCE = "system_inference"


@dataclass(frozen=True)
class CampaignStateTransitionEvidence:
    """Evidence supporting a proposed state transition."""

    source: CampaignStateTransitionSource | str
    summary: str
    quote: str = ""
    path: List[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def path_text(self) -> str:
        return " > ".join(part for part in self.path if part)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source"] = _enum_value(self.source)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignStateTransitionEvidence":
        return cls(
            source=str(data.get("source", CampaignStateTransitionSource.SYSTEM_INFERENCE.value)),
            summary=str(data.get("summary", "")),
            quote=str(data.get("quote", "")),
            path=[str(item) for item in data.get("path", [])],
            confidence=float(data.get("confidence", 0.5)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class CampaignStateTransitionProposal:
    """A proposed campaign/sandbox/donjon state transition.

    This object never applies state changes by itself. It is an advisory proposal
    that a later approval/state-store layer may accept, revise, reject, or apply.
    """

    proposal_id: str
    campaign_id: str
    scene_id: str
    transition_type: CampaignStateTransitionType | str
    title: str
    summary: str
    source: CampaignStateTransitionSource | str = CampaignStateTransitionSource.SYSTEM_INFERENCE
    risk: CampaignStateTransitionRisk | str = CampaignStateTransitionRisk.MEDIUM
    approval_status: CampaignStateTransitionApprovalStatus | str = CampaignStateTransitionApprovalStatus.PROPOSED
    approval_required: bool = True
    evidence: List[CampaignStateTransitionEvidence] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)
    state_patch_preview: Dict[str, Any] = field(default_factory=dict)
    player_visible_summary: str = ""
    dm_only_notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_applyable_without_approval(self) -> bool:
        return (not self.approval_required) and _enum_value(self.risk) == CampaignStateTransitionRisk.LOW.value

    @property
    def requires_human_review(self) -> bool:
        return self.approval_required or _enum_value(self.risk) in {
            CampaignStateTransitionRisk.HIGH.value,
            CampaignStateTransitionRisk.IRREVERSIBLE.value,
        }

    def approved(self) -> "CampaignStateTransitionProposal":
        return self.with_status(CampaignStateTransitionApprovalStatus.APPROVED)

    def rejected(self) -> "CampaignStateTransitionProposal":
        return self.with_status(CampaignStateTransitionApprovalStatus.REJECTED)

    def with_status(
        self,
        status: CampaignStateTransitionApprovalStatus | str,
    ) -> "CampaignStateTransitionProposal":
        return CampaignStateTransitionProposal(
            proposal_id=self.proposal_id,
            campaign_id=self.campaign_id,
            scene_id=self.scene_id,
            transition_type=self.transition_type,
            title=self.title,
            summary=self.summary,
            source=self.source,
            risk=self.risk,
            approval_status=status,
            approval_required=self.approval_required,
            evidence=list(self.evidence),
            recommended_next_steps=list(self.recommended_next_steps),
            state_patch_preview=dict(self.state_patch_preview),
            player_visible_summary=self.player_visible_summary,
            dm_only_notes=list(self.dm_only_notes),
            tags=list(self.tags),
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["transition_type"] = _enum_value(self.transition_type)
        data["source"] = _enum_value(self.source)
        data["risk"] = _enum_value(self.risk)
        data["approval_status"] = _enum_value(self.approval_status)
        data["evidence"] = [item.to_dict() for item in self.evidence]
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignStateTransitionProposal":
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            campaign_id=str(data.get("campaign_id", "")),
            scene_id=str(data.get("scene_id", "")),
            transition_type=str(data.get("transition_type", CampaignStateTransitionType.DM_REVIEW_REQUIRED.value)),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            source=str(data.get("source", CampaignStateTransitionSource.SYSTEM_INFERENCE.value)),
            risk=str(data.get("risk", CampaignStateTransitionRisk.MEDIUM.value)),
            approval_status=str(data.get("approval_status", CampaignStateTransitionApprovalStatus.PROPOSED.value)),
            approval_required=bool(data.get("approval_required", True)),
            evidence=[CampaignStateTransitionEvidence.from_dict(item) for item in data.get("evidence", [])],
            recommended_next_steps=[str(item) for item in data.get("recommended_next_steps", [])],
            state_patch_preview=dict(data.get("state_patch_preview", {})),
            player_visible_summary=str(data.get("player_visible_summary", "")),
            dm_only_notes=[str(item) for item in data.get("dm_only_notes", [])],
            tags=[str(item) for item in data.get("tags", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class CampaignStateTransitionProposalResult:
    """Container for one proposal batch."""

    campaign_id: str
    scene_id: str
    proposals: List[CampaignStateTransitionProposal] = field(default_factory=list)
    summary: str = ""
    approval_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.proposals)

    @property
    def pending_approval_count(self) -> int:
        return sum(1 for proposal in self.proposals if proposal.requires_human_review)

    def by_type(
        self,
        transition_type: CampaignStateTransitionType | str,
    ) -> List[CampaignStateTransitionProposal]:
        wanted = _enum_value(transition_type)
        return [proposal for proposal in self.proposals if _enum_value(proposal.transition_type) == wanted]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "scene_id": self.scene_id,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "summary": self.summary,
            "approval_required": self.approval_required,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CampaignStateTransitionProposalResult":
        return cls(
            campaign_id=str(data.get("campaign_id", "")),
            scene_id=str(data.get("scene_id", "")),
            proposals=[CampaignStateTransitionProposal.from_dict(item) for item in data.get("proposals", [])],
            summary=str(data.get("summary", "")),
            approval_required=bool(data.get("approval_required", True)),
            metadata=dict(data.get("metadata", {})),
        )


def build_proposal_id(
    campaign_id: str,
    scene_id: str,
    transition_type: CampaignStateTransitionType | str,
    title: str,
) -> str:
    """Build a stable, human-readable proposal id."""
    return ":".join([
        _slugify(campaign_id or "campaign"),
        _slugify(scene_id or "scene"),
        _slugify(_enum_value(transition_type)),
        _slugify(title or "proposal"),
    ])


def proposal_requires_approval(
    transition_type: CampaignStateTransitionType | str,
    risk: CampaignStateTransitionRisk | str = CampaignStateTransitionRisk.MEDIUM,
) -> bool:
    """Default approval rule for G1.1 models.

    Later G1 approval policy may replace this. The initial model-level rule is
    conservative: only low-risk scene/location bookkeeping can be auto-safe.
    """
    transition = _enum_value(transition_type)
    risk_value = _enum_value(risk)
    if risk_value != CampaignStateTransitionRisk.LOW.value:
        return True
    return transition not in {
        CampaignStateTransitionType.SCENE_ENTERED.value,
        CampaignStateTransitionType.ROOM_ENTERED.value,
        CampaignStateTransitionType.LOCATION_UNLOCKED.value,
    }


def _enum_value(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else str(value or "")


def _slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    chars = []
    last_dash = False
    for ch in text:
        if ch.isalnum():
            chars.append(ch)
            last_dash = False
        elif not last_dash:
            chars.append("-")
            last_dash = True
    slug = "".join(chars).strip("-")
    return slug or "item"
