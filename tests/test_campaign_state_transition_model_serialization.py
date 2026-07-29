import json

from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionEvidence,
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionSource,
    CampaignStateTransitionType,
)


def test_campaign_state_transition_proposal_round_trip_serialization():
    proposal = CampaignStateTransitionProposal(
        proposal_id="lmop:goblin-ambush:xp-award-candidate:goblin-xp",
        campaign_id="lmop",
        scene_id="goblin-ambush",
        transition_type=CampaignStateTransitionType.XP_AWARD_CANDIDATE,
        title="Goblin ambush XP candidate",
        summary="The module indicates XP may be awarded after the encounter.",
        source=CampaignStateTransitionSource.MODULE_CONTENT,
        risk=CampaignStateTransitionRisk.MEDIUM,
        approval_required=True,
        evidence=[CampaignStateTransitionEvidence(
            source=CampaignStateTransitionSource.MODULE_CONTENT,
            summary="Awarding Experience Points section detected.",
            quote="Divide XP equally among the characters.",
            confidence=0.9,
        )],
        recommended_next_steps=["Ask the DM to approve XP award."],
        state_patch_preview={"xp_award_candidate": True},
        tags=["lmop", "xp"],
    )

    data = proposal.to_dict()
    encoded = json.dumps(data)
    decoded = json.loads(encoded)
    restored = CampaignStateTransitionProposal.from_dict(decoded)

    assert restored.proposal_id == proposal.proposal_id
    assert restored.transition_type == CampaignStateTransitionType.XP_AWARD_CANDIDATE.value
    assert restored.source == CampaignStateTransitionSource.MODULE_CONTENT.value
    assert restored.risk == CampaignStateTransitionRisk.MEDIUM.value
    assert restored.evidence[0].summary == "Awarding Experience Points section detected."
    assert restored.state_patch_preview == {"xp_award_candidate": True}


def test_campaign_state_transition_result_round_trip_serialization():
    proposal = CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="sandbox",
        scene_id="npc-talk",
        transition_type=CampaignStateTransitionType.NPC_INFO_REVEALED,
        title="NPC clue candidate",
        summary="NPC may reveal a quest clue.",
    )
    result = CampaignStateTransitionProposalResult(
        campaign_id="sandbox",
        scene_id="npc-talk",
        proposals=[proposal],
        summary="One proposal generated.",
    )

    restored = CampaignStateTransitionProposalResult.from_dict(result.to_dict())

    assert restored.ok is True
    assert restored.campaign_id == "sandbox"
    assert restored.proposals[0].transition_type == CampaignStateTransitionType.NPC_INFO_REVEALED.value
    assert restored.summary == "One proposal generated."
