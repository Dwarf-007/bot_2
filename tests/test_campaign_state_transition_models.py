from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionApprovalStatus,
    CampaignStateTransitionEvidence,
    CampaignStateTransitionProposal,
    CampaignStateTransitionProposalResult,
    CampaignStateTransitionRisk,
    CampaignStateTransitionSource,
    CampaignStateTransitionType,
    build_proposal_id,
    proposal_requires_approval,
)


def test_campaign_state_transition_proposal_supports_dm_approval_flow():
    evidence = CampaignStateTransitionEvidence(
        source=CampaignStateTransitionSource.MODULE_CONTENT,
        summary="Module text indicates four goblins are hiding and may attack.",
        quote="Four goblins are hiding in the woods.",
        path=["Lost Mine", "Goblin Ambush"],
        confidence=0.82,
    )
    proposal = CampaignStateTransitionProposal(
        proposal_id=build_proposal_id("lmop", "goblin-ambush", CampaignStateTransitionType.ENCOUNTER_SUGGESTED, "Goblin ambush encounter candidate"),
        campaign_id="lmop",
        scene_id="goblin-ambush",
        transition_type=CampaignStateTransitionType.ENCOUNTER_SUGGESTED,
        title="Goblin ambush encounter candidate",
        summary="The module indicates a possible goblin ambush encounter.",
        source=CampaignStateTransitionSource.MODULE_CONTENT,
        risk=CampaignStateTransitionRisk.HIGH,
        approval_required=True,
        evidence=[evidence],
        recommended_next_steps=["Ask DM whether to start combat."],
    )

    assert proposal.proposal_id == "lmop:goblin-ambush:encounter-suggested:goblin-ambush-encounter-candidate"
    assert proposal.requires_human_review is True
    assert proposal.is_applyable_without_approval is False
    assert proposal.evidence[0].path_text == "Lost Mine > Goblin Ambush"

    approved = proposal.approved()
    assert approved.approval_status == CampaignStateTransitionApprovalStatus.APPROVED
    assert proposal.approval_status == CampaignStateTransitionApprovalStatus.PROPOSED


def test_low_risk_scene_entered_can_be_auto_safe_by_default():
    assert proposal_requires_approval(CampaignStateTransitionType.SCENE_ENTERED, CampaignStateTransitionRisk.LOW) is False
    assert proposal_requires_approval(CampaignStateTransitionType.ROOM_ENTERED, CampaignStateTransitionRisk.LOW) is False
    assert proposal_requires_approval(CampaignStateTransitionType.ENCOUNTER_STARTED, CampaignStateTransitionRisk.LOW) is True
    assert proposal_requires_approval(CampaignStateTransitionType.TREASURE_AWARDED, CampaignStateTransitionRisk.LOW) is True
    assert proposal_requires_approval(CampaignStateTransitionType.SCENE_ENTERED, CampaignStateTransitionRisk.MEDIUM) is True


def test_campaign_state_transition_result_filters_by_type_and_counts_pending_approval():
    p1 = CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="lmop",
        scene_id="s1",
        transition_type=CampaignStateTransitionType.ENCOUNTER_SUGGESTED,
        title="Encounter",
        summary="Encounter candidate.",
        approval_required=True,
        risk=CampaignStateTransitionRisk.HIGH,
    )
    p2 = CampaignStateTransitionProposal(
        proposal_id="p2",
        campaign_id="lmop",
        scene_id="s1",
        transition_type=CampaignStateTransitionType.SCENE_ENTERED,
        title="Scene entered",
        summary="Scene opened.",
        approval_required=False,
        risk=CampaignStateTransitionRisk.LOW,
    )
    result = CampaignStateTransitionProposalResult(campaign_id="lmop", scene_id="s1", proposals=[p1, p2])

    assert result.ok is True
    assert result.pending_approval_count == 1
    assert result.by_type(CampaignStateTransitionType.ENCOUNTER_SUGGESTED) == [p1]
    assert result.by_type("scene_entered") == [p2]
