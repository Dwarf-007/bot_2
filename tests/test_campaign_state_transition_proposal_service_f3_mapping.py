from services.compendium.campaign_content_advisor import CampaignContentAdvice, CampaignContentHint, CampaignContentKind
from services.compendium.campaign_state_transition_models import CampaignStateTransitionType
from services.compendium.campaign_state_transition_proposal_service import CampaignStateTransitionProposalRequest, CampaignStateTransitionProposalService


def test_service_maps_treasure_npc_and_development_hints():
    advice = CampaignContentAdvice(
        query="Phandalin",
        found=True,
        treasure_hints=[CampaignContentHint(kind=CampaignContentKind.TREASURE, title="Treasure", snippet="16 sp and 7 gp.", extracted_entities=["16 sp", "7 gp"])],
        npc_hints=[CampaignContentHint(kind=CampaignContentKind.NPC, title="Important NPCs", snippet="Toblen Stonehill, innkeeper.")],
        development_hints=[CampaignContentHint(kind=CampaignContentKind.DEVELOPMENT, title="Developments", snippet="If the players need direction, an NPC points them onward.")],
    )
    result = CampaignStateTransitionProposalService().propose(CampaignStateTransitionProposalRequest(
        campaign_id="lmop",
        scene_id="phandalin",
        advice=advice,
        tags=["module:lmop"],
    ))

    by_type = {proposal.transition_type: proposal for proposal in result.proposals}
    assert CampaignStateTransitionType.TREASURE_DISCOVERED in by_type
    assert CampaignStateTransitionType.NPC_INFO_REVEALED in by_type
    assert CampaignStateTransitionType.BRANCH_AVAILABLE in by_type
    assert "module:lmop" in by_type[CampaignStateTransitionType.TREASURE_DISCOVERED].tags
    assert by_type[CampaignStateTransitionType.TREASURE_DISCOVERED].approval_required is True
    assert by_type[CampaignStateTransitionType.NPC_INFO_REVEALED].approval_required is True
