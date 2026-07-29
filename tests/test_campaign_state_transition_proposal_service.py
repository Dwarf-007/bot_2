from services.compendium.campaign_content_advisor import CampaignContentAdvice, CampaignContentHint, CampaignContentKind
from services.compendium.campaign_state_transition_models import CampaignStateTransitionType
from services.compendium.campaign_state_transition_proposal_service import (
    CampaignStateTransitionProposalRequest,
    CampaignStateTransitionProposalService,
)


def _hint(kind, title="Goblin Ambush", snippet="Four goblins are hiding in the woods.", entities=None):
    return CampaignContentHint(
        kind=kind,
        title=title,
        path=["Lost Mine", title],
        snippet=snippet,
        confidence=0.88,
        extracted_entities=entities or [],
        automation_hint="DM approval recommended.",
    )


def test_proposal_service_maps_campaign_content_hints_to_transition_proposals():
    advice = CampaignContentAdvice(
        query="Goblin Ambush",
        found=True,
        read_aloud_candidates=[_hint(CampaignContentKind.READ_ALOUD, snippet="Two dead horses block the path.")],
        encounter_hints=[_hint(CampaignContentKind.ENCOUNTER, entities=["goblin"])],
        development_hints=[_hint(CampaignContentKind.DEVELOPMENT, title="Developments", snippet="The characters might capture goblins.")],
        reward_hints=[_hint(CampaignContentKind.REWARD, title="Awarding Experience Points", snippet="Award 75 XP.", entities=["75 XP"])],
    )
    request = CampaignStateTransitionProposalRequest(
        campaign_id="lmop",
        scene_id="goblin-ambush",
        advice=advice,
        party_action_summary="The party approached the dead horses.",
    )

    result = CampaignStateTransitionProposalService().propose(request)
    types = {proposal.transition_type for proposal in result.proposals}

    assert result.ok is True
    assert result.approval_required is True
    assert CampaignStateTransitionType.SCENE_ENTERED in types
    assert CampaignStateTransitionType.ENCOUNTER_SUGGESTED in types
    assert CampaignStateTransitionType.BRANCH_AVAILABLE in types
    assert CampaignStateTransitionType.XP_AWARD_CANDIDATE in types
    assert result.pending_approval_count == len(result.proposals)
    assert any("initiative" in " ".join(p.recommended_next_steps).lower() for p in result.proposals)


def test_proposal_service_generates_dm_review_when_advice_not_found():
    advice = CampaignContentAdvice(query="Unknown", found=False)
    request = CampaignStateTransitionProposalRequest(campaign_id="lmop", scene_id="unknown", advice=advice)

    result = CampaignStateTransitionProposalService().propose(request)

    assert result.ok is True
    assert len(result.proposals) == 1
    assert result.proposals[0].transition_type == CampaignStateTransitionType.DM_REVIEW_REQUIRED
    assert result.proposals[0].approval_required is True


def test_proposal_service_preserves_evidence_and_state_patch_preview():
    advice = CampaignContentAdvice(
        query="Trapped Hall",
        found=True,
        trap_hints=[_hint(CampaignContentKind.TRAP, "Trapped Hall", "DC 15, {@damage 2d6}, {@condition prone}.", ["DC 15", "2d6", "prone"])],
    )
    request = CampaignStateTransitionProposalRequest(campaign_id="lmop", scene_id="trapped-hall", advice=advice)

    result = CampaignStateTransitionProposalService().propose(request)
    proposal = result.proposals[0]

    assert proposal.transition_type == CampaignStateTransitionType.TRAP_DETECTED
    assert proposal.state_patch_preview["trap_candidate"] is True
    assert proposal.evidence[0].path_text == "Lost Mine > Trapped Hall"
    assert "DC 15" in proposal.evidence[0].metadata["extracted_entities"]
    assert proposal.requires_human_review is True
