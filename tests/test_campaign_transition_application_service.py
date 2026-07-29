from services.campaign.campaign_state_store import CampaignStateStore
from services.campaign.campaign_transition_application_service import (
    CampaignTransitionApplicationService,
    CampaignTransitionApplicationStatus,
)
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)


def _proposal(transition_type, approved=True, **kwargs):
    return CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="c1",
        scene_id="s1",
        transition_type=transition_type,
        title="Proposal",
        summary="Summary",
        risk=kwargs.pop("risk", CampaignStateTransitionRisk.LOW),
        approval_required=kwargs.pop("approval_required", False),
        approval_status=CampaignStateTransitionApprovalStatus.APPROVED if approved else CampaignStateTransitionApprovalStatus.PROPOSED,
        **kwargs,
    )


def test_application_service_applies_approved_location_unlock():
    store = CampaignStateStore()
    service = CampaignTransitionApplicationService(store)
    proposal = _proposal(
        CampaignStateTransitionType.LOCATION_UNLOCKED,
        state_patch_preview={"location_id": "old-watchtower", "title": "Old Watchtower"},
    )

    result = service.apply_proposals("c1", "s1", [proposal])

    assert result.applied_count == 1
    state = store.get_campaign("c1")
    assert state is not None
    assert "old-watchtower" in state.locations
    assert "old-watchtower" in state.knowledge.known_locations


def test_application_service_skips_unapproved_proposal():
    service = CampaignTransitionApplicationService(CampaignStateStore())
    proposal = _proposal(CampaignStateTransitionType.LOCATION_UNLOCKED, approved=False)

    result = service.apply_proposals("c1", "s1", [proposal])

    assert result.applied_count == 0
    assert result.records[0].status == CampaignTransitionApplicationStatus.SKIPPED


def test_application_service_blocks_never_auto_branch_selected():
    service = CampaignTransitionApplicationService(CampaignStateStore())
    proposal = _proposal(
        CampaignStateTransitionType.BRANCH_SELECTED,
        risk=CampaignStateTransitionRisk.HIGH,
        approval_required=True,
    )

    result = service.apply_proposals("c1", "s1", [proposal], require_approved_status=False)

    assert result.applied_count == 0
    assert result.blocked_count == 1
    assert result.records[0].status == CampaignTransitionApplicationStatus.BLOCKED


def test_application_service_applies_knowledge_update():
    service = CampaignTransitionApplicationService(CampaignStateStore())
    proposal = _proposal(
        CampaignStateTransitionType.QUEST_CLUE_DISCOVERED,
        summary="The tower is connected to the caravan disappearances.",
        player_visible_summary="A new clue points to the old tower.",
    )

    result = service.apply_proposals("c1", "s1", [proposal])

    assert result.applied_count == 1
    state = result.state
    assert "A new clue points to the old tower." in state.knowledge.known_clues
