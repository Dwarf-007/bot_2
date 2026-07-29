from core.turn_output import TurnOutput
from services.compendium.campaign_content_advisor import CampaignContentAdvice, CampaignContentHint, CampaignContentKind
from services.compendium.campaign_state_transition_application_service import (
    CampaignStateTransitionApplicationRequest,
    CampaignStateTransitionApplicationService,
)
from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_state_transition_proposal_service import CampaignStateTransitionProposalRequest


def _advice():
    return CampaignContentAdvice(
        query="Goblin Ambush",
        found=True,
        encounter_hints=[CampaignContentHint(kind=CampaignContentKind.ENCOUNTER, title="Goblin Ambush", snippet="Four goblins are hiding in the woods.")],
        reward_hints=[CampaignContentHint(kind=CampaignContentKind.REWARD, title="Award XP", snippet="75 XP", extracted_entities=["75 XP"])],
    )


def test_application_service_maps_proposal_request_to_turn_output():
    service = CampaignStateTransitionApplicationService()
    request = CampaignStateTransitionProposalRequest(
        campaign_id="lmop",
        scene_id="goblin-ambush",
        advice=_advice(),
    )

    output = service.advise(request)

    assert isinstance(output, TurnOutput)
    assert "Campaign State Transition Advisory" in output.public_narrative
    assert "Goblin Ambush" in output.public_narrative
    assert "DM approval" in output.public_narrative
    assert output.suggested_commands == []
    assert output.avrae_commands == []
    assert any("Approval policy summary" in item for item in output.dm_instructions)
    assert any("encounter_suggested" in item for item in output.dm_instructions)
    assert any("Evidence" in item for item in output.dm_instructions)


def test_application_service_accepts_proposal_result_directly():
    proposal = CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="sandbox",
        scene_id="npc-talk",
        transition_type=CampaignStateTransitionType.NPC_INFO_REVEALED,
        title="NPC clue candidate",
        summary="NPC may reveal a quest clue.",
        risk=CampaignStateTransitionRisk.MEDIUM,
        approval_required=True,
    )
    result = CampaignStateTransitionProposalResult(campaign_id="sandbox", scene_id="npc-talk", proposals=[proposal])

    output = CampaignStateTransitionApplicationService().advise(result)

    assert "NPC clue candidate" in output.public_narrative
    assert "dm_approval_required" in "
".join(output.dm_instructions)
    assert output.suggested_commands == []


def test_application_service_detects_never_auto_policy_in_public_narrative():
    proposal = CampaignStateTransitionProposal(
        proposal_id="p2",
        campaign_id="lmop",
        scene_id="branch",
        transition_type=CampaignStateTransitionType.BRANCH_SELECTED,
        title="Branch selected candidate",
        summary="A story branch would be selected.",
        risk=CampaignStateTransitionRisk.HIGH,
        approval_required=True,
    )
    result = CampaignStateTransitionProposalResult(campaign_id="lmop", scene_id="branch", proposals=[proposal])

    output = CampaignStateTransitionApplicationService().advise(result)

    assert "never-auto" in output.public_narrative
    assert "NEVER_AUTO" not in output.public_narrative
    assert "never_auto" in "
".join(output.dm_instructions)


def test_application_service_handles_empty_request_safely():
    output = CampaignStateTransitionApplicationService().advise({"campaign_id": "lmop", "scene_id": "unknown"})

    assert "No state transition proposals were generated" in output.public_narrative
    assert output.suggested_commands == []
    assert output.avrae_commands == []
