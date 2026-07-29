from services.campaign.campaign_state_store import CampaignStateStore
from services.campaign.campaign_transition_application_service import CampaignTransitionApplicationService
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)


class FakeCampaignProgressRepository:
    def __init__(self):
        self.progress_calls = []
        self.objective_calls = []

    def set_channel_progress(self, **kwargs):
        self.progress_calls.append(kwargs)

    def add_objective(self, **kwargs):
        self.objective_calls.append(kwargs)
        return 1


def test_scene_entered_bridges_to_campaign_progress_repository():
    repo = FakeCampaignProgressRepository()
    service = CampaignTransitionApplicationService(CampaignStateStore(), campaign_progress_repository=repo)
    proposal = CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="c1",
        scene_id="s1",
        transition_type=CampaignStateTransitionType.SCENE_ENTERED,
        title="Scene entered",
        summary="Scene entered.",
        risk=CampaignStateTransitionRisk.LOW,
        approval_required=False,
        approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
        state_patch_preview={"scene_id": "s1", "room_id": "r1"},
    )

    result = service.apply_proposals("c1", "s1", [proposal], channel_id="ch1")

    assert result.applied_count == 1
    assert repo.progress_calls
    assert repo.progress_calls[0]["current_scene_id"] == "s1"
    assert repo.progress_calls[0]["current_room_id"] == "r1"


def test_branch_available_bridges_to_objective_repository():
    repo = FakeCampaignProgressRepository()
    service = CampaignTransitionApplicationService(CampaignStateStore(), campaign_progress_repository=repo)
    proposal = CampaignStateTransitionProposal(
        proposal_id="p2",
        campaign_id="c1",
        scene_id="s2",
        transition_type=CampaignStateTransitionType.BRANCH_AVAILABLE,
        title="Branch available",
        summary="A new lead is available.",
        risk=CampaignStateTransitionRisk.MEDIUM,
        approval_required=True,
        approval_status=CampaignStateTransitionApprovalStatus.APPROVED,
        recommended_next_steps=["Follow the trail."],
    )

    result = service.apply_proposals("c1", "s2", [proposal], channel_id="ch1")

    assert result.applied_count == 1
    assert repo.objective_calls
    assert repo.objective_calls[0]["text"] == "A new lead is available."
