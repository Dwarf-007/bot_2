from services.compendium.campaign_content_advisor import CampaignContentAdvice, CampaignContentHint, CampaignContentKind
from services.compendium.campaign_state_transition_models import CampaignStateTransitionType
from services.compendium.campaign_state_transition_proposal_service import (
    CampaignStateTransitionProposalRequest,
    CampaignStateTransitionProposalService,
)
from services.compendium.campaign_transition_approval_policy import (
    CampaignTransitionApprovalCategory,
    CampaignTransitionApprovalPolicy,
)


def test_policy_classifies_proposals_generated_by_g1_2_service():
    advice = CampaignContentAdvice(
        query="Goblin Ambush",
        found=True,
        encounter_hints=[CampaignContentHint(kind=CampaignContentKind.ENCOUNTER, title="Goblin Ambush", snippet="Four goblins attack.")],
        reward_hints=[CampaignContentHint(kind=CampaignContentKind.REWARD, title="Award XP", snippet="75 XP", extracted_entities=["75 XP"])],
    )
    result = CampaignStateTransitionProposalService().propose(CampaignStateTransitionProposalRequest(
        campaign_id="lmop",
        scene_id="goblin-ambush",
        advice=advice,
    ))

    decisions = CampaignTransitionApprovalPolicy().decide_batch(result.proposals)
    by_type = {decision.transition_type: decision for decision in decisions.decisions}

    assert by_type[CampaignStateTransitionType.ENCOUNTER_SUGGESTED.value].category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED
    assert by_type[CampaignStateTransitionType.XP_AWARD_CANDIDATE.value].category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED
    assert decisions.requires_dm_approval is True
    assert decisions.has_never_auto is False
