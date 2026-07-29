"""
SERVICES/CAMPAIGN/CAMPAIGN_TRANSITION_APPLICATION_SERVICE.PY
Applies approved G1 CampaignStateTransitionProposal objects to the G2 campaign state layer.

G2.3 purpose:
- Start the approved proposal -> campaign state update path.
- Apply only safe/approved transitions.
- Integrate with the in-memory CampaignStateStore from G2.2.
- Optionally bridge selected transitions to existing repository APIs such as
  CampaignProgressRepository.

Boundary:
- No Discord I/O.
- No Avrae integration.
- No LLM calls.
- No automatic application of unapproved or never-auto proposals.
- No irreversible campaign mutation without explicit approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from services.campaign.campaign_state_models import (
    CampaignState,
    LocationState,
    QuestState,
    QuestStatus,
)
from services.campaign.campaign_state_store import CampaignStateStore
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_transition_approval_policy import (
    CampaignTransitionApprovalCategory,
    CampaignTransitionApprovalPolicy,
)


class CampaignTransitionApplicationStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CampaignTransitionApplicationRecord:
    proposal_id: str
    transition_type: str
    status: CampaignTransitionApplicationStatus | str
    summary: str
    applied_changes: List[str] = field(default_factory=list)
    blocking_reasons: List[str] = field(default_factory=list)

    @property
    def applied(self) -> bool:
        return self.status == CampaignTransitionApplicationStatus.APPLIED


@dataclass(frozen=True)
class CampaignTransitionApplicationResult:
    campaign_id: str
    scene_id: str
    records: List[CampaignTransitionApplicationRecord] = field(default_factory=list)
    state: Optional[CampaignState] = None
    summary: str = ""

    @property
    def applied_count(self) -> int:
        return sum(1 for record in self.records if record.applied)

    @property
    def blocked_count(self) -> int:
        return sum(1 for record in self.records if record.status == CampaignTransitionApplicationStatus.BLOCKED)


class CampaignTransitionApplicationService:
    """Applies approved transition proposals to CampaignStateStore.

    Repository hooks are intentionally optional. This keeps the G2.3 foundation
    testable without a database while allowing later integration with existing
    repository classes:
    - CampaignProgressRepository
    - LocationRepository
    - CampaignRepository
    - RoomAliasRepository
    """

    def __init__(
        self,
        state_store: CampaignStateStore,
        approval_policy: Optional[CampaignTransitionApprovalPolicy] = None,
        campaign_progress_repository: Any | None = None,
        location_repository: Any | None = None,
        campaign_repository: Any | None = None,
        room_alias_repository: Any | None = None,
    ) -> None:
        self.state_store = state_store
        self.approval_policy = approval_policy or CampaignTransitionApprovalPolicy()
        self.campaign_progress_repository = campaign_progress_repository
        self.location_repository = location_repository
        self.campaign_repository = campaign_repository
        self.room_alias_repository = room_alias_repository

    def apply_proposals(
        self,
        campaign_id: str,
        scene_id: str,
        proposals: Iterable[CampaignStateTransitionProposal],
        require_approved_status: bool = True,
        channel_id: str = "",
    ) -> CampaignTransitionApplicationResult:
        state = self._get_or_create_state(campaign_id)
        records: List[CampaignTransitionApplicationRecord] = []

        for proposal in proposals:
            record = self.apply_proposal(
                state=state,
                proposal=proposal,
                require_approved_status=require_approved_status,
                channel_id=channel_id,
            )
            records.append(record)

        self.state_store.save_campaign(state)
        return CampaignTransitionApplicationResult(
            campaign_id=campaign_id,
            scene_id=scene_id,
            records=records,
            state=state,
            summary=f"Applied {sum(1 for record in records if record.applied)} of {len(records)} proposal(s).",
        )

    def apply_proposal(
        self,
        state: CampaignState,
        proposal: CampaignStateTransitionProposal,
        require_approved_status: bool = True,
        channel_id: str = "",
    ) -> CampaignTransitionApplicationRecord:
        decision = self.approval_policy.decide(proposal)
        transition_type = self._transition_value(proposal.transition_type)

        if decision.category == CampaignTransitionApprovalCategory.NEVER_AUTO:
            return CampaignTransitionApplicationRecord(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                status=CampaignTransitionApplicationStatus.BLOCKED,
                summary="Proposal is never-auto and was not applied.",
                blocking_reasons=list(decision.blocking_reasons),
            )

        if require_approved_status and self._status_value(proposal.approval_status) != CampaignStateTransitionApprovalStatus.APPROVED.value:
            return CampaignTransitionApplicationRecord(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                status=CampaignTransitionApplicationStatus.SKIPPED,
                summary="Proposal is not approved and was not applied.",
                blocking_reasons=["approval_status is not approved"],
            )

        changes: List[str] = []
        if transition_type in {CampaignStateTransitionType.SCENE_ENTERED.value, CampaignStateTransitionType.ROOM_ENTERED.value}:
            changes.extend(self._apply_scene_or_room_entered(state, proposal, channel_id=channel_id))
        elif transition_type == CampaignStateTransitionType.LOCATION_UNLOCKED.value:
            changes.extend(self._apply_location_unlocked(state, proposal))
        elif transition_type in {CampaignStateTransitionType.QUEST_CLUE_DISCOVERED.value, CampaignStateTransitionType.NPC_INFO_REVEALED.value}:
            changes.extend(self._apply_knowledge_update(state, proposal))
        elif transition_type in {CampaignStateTransitionType.BRANCH_AVAILABLE.value, CampaignStateTransitionType.QUEST_UPDATED.value}:
            changes.extend(self._apply_objective_candidate(state, proposal, channel_id=channel_id))
        elif transition_type == CampaignStateTransitionType.SCENE_COMPLETED.value:
            changes.extend(self._apply_scene_completed(state, proposal, channel_id=channel_id))
        else:
            return CampaignTransitionApplicationRecord(
                proposal_id=proposal.proposal_id,
                transition_type=transition_type,
                status=CampaignTransitionApplicationStatus.SKIPPED,
                summary="Transition type is not handled by G2.3 foundation service.",
                blocking_reasons=["unsupported transition type in G2.3"],
            )

        return CampaignTransitionApplicationRecord(
            proposal_id=proposal.proposal_id,
            transition_type=transition_type,
            status=CampaignTransitionApplicationStatus.APPLIED,
            summary="Approved proposal was applied to CampaignStateStore.",
            applied_changes=changes,
        )

    def _get_or_create_state(self, campaign_id: str) -> CampaignState:
        existing = self.state_store.get_campaign(campaign_id)
        if existing is not None:
            return existing
        title = campaign_id
        if self.campaign_repository is not None and hasattr(self.campaign_repository, "get_campaign"):
            record = self.campaign_repository.get_campaign(campaign_id)
            if record is not None:
                title = getattr(record, "name", campaign_id) or campaign_id
        state = CampaignState(campaign_id=campaign_id, title=title)
        self.state_store.save_campaign(state)
        return state

    def _apply_scene_or_room_entered(self, state: CampaignState, proposal: CampaignStateTransitionProposal, channel_id: str = "") -> List[str]:
        changes: List[str] = []
        patch = proposal.state_patch_preview or {}
        scene_id = str(patch.get("scene_id") or proposal.scene_id or "")
        room_id = str(patch.get("room_id") or patch.get("location_id") or "")
        if scene_id:
            state.active_location_id = room_id or state.active_location_id
            changes.append(f"scene_entered:{scene_id}")
        if room_id:
            state.locations.setdefault(room_id, LocationState(location_id=room_id, name=room_id, discovered=True, visited=True))
            state.locations[room_id].discovered = True
            state.locations[room_id].visited = True
            if room_id not in state.knowledge.known_locations:
                state.knowledge.known_locations.append(room_id)
            changes.append(f"room_entered:{room_id}")
        if self.campaign_progress_repository is not None and channel_id and hasattr(self.campaign_progress_repository, "set_channel_progress"):
            self.campaign_progress_repository.set_channel_progress(
                channel_id=channel_id,
                campaign_id=state.campaign_id,
                current_scene_id=scene_id or None,
                current_room_id=room_id or None,
                milestone="scene_entered",
                metadata={"proposal_id": proposal.proposal_id},
            )
            changes.append("campaign_progress_repository.set_channel_progress")
        return changes or ["scene_or_room_entered:no-op"]

    def _apply_location_unlocked(self, state: CampaignState, proposal: CampaignStateTransitionProposal) -> List[str]:
        patch = proposal.state_patch_preview or {}
        location_id = str(patch.get("location_id") or patch.get("room_id") or proposal.scene_id or "location").strip()
        title = str(patch.get("title") or patch.get("name") or location_id)
        state.locations.setdefault(location_id, LocationState(location_id=location_id, name=title))
        state.locations[location_id].discovered = True
        if location_id not in state.knowledge.known_locations:
            state.knowledge.known_locations.append(location_id)
        return [f"location_unlocked:{location_id}"]

    def _apply_knowledge_update(self, state: CampaignState, proposal: CampaignStateTransitionProposal) -> List[str]:
        clue = proposal.player_visible_summary or proposal.summary or proposal.title
        if clue and clue not in state.knowledge.known_clues:
            state.knowledge.known_clues.append(clue)
        return ["party_knowledge.updated"]

    def _apply_objective_candidate(self, state: CampaignState, proposal: CampaignStateTransitionProposal, channel_id: str = "") -> List[str]:
        quest_id = proposal.proposal_id
        title = proposal.title
        state.quests.setdefault(
            quest_id,
            QuestState(
                quest_id=quest_id,
                title=title,
                status=QuestStatus.ACTIVE,
                known_clues=[proposal.summary],
                next_leads=list(proposal.recommended_next_steps),
            ),
        )
        changes = [f"quest_candidate:{quest_id}"]
        if self.campaign_progress_repository is not None and channel_id and hasattr(self.campaign_progress_repository, "add_objective"):
            self.campaign_progress_repository.add_objective(
                channel_id=channel_id,
                campaign_id=state.campaign_id,
                text=proposal.summary or proposal.title,
                scene_id=proposal.scene_id,
                room_id=(proposal.state_patch_preview or {}).get("room_id"),
            )
            changes.append("campaign_progress_repository.add_objective")
        return changes

    def _apply_scene_completed(self, state: CampaignState, proposal: CampaignStateTransitionProposal, channel_id: str = "") -> List[str]:
        changes = [f"scene_completed:{proposal.scene_id}"]
        if self.campaign_progress_repository is not None and channel_id and hasattr(self.campaign_progress_repository, "set_channel_progress"):
            self.campaign_progress_repository.set_channel_progress(
                channel_id=channel_id,
                campaign_id=state.campaign_id,
                current_scene_id=proposal.scene_id,
                milestone="scene_completed",
                metadata={"proposal_id": proposal.proposal_id},
            )
            changes.append("campaign_progress_repository.set_channel_progress")
        return changes

    @staticmethod
    def _transition_value(value: CampaignStateTransitionType | str) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _status_value(value: CampaignStateTransitionApprovalStatus | str) -> str:
        return value.value if hasattr(value, "value") else str(value)
