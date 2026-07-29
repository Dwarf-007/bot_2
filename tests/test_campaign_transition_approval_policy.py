from services.compendium.campaign_state_transition_models import (
    CampaignStateTransitionProposal,
    CampaignStateTransitionRisk,
    CampaignStateTransitionType,
)
from services.compendium.campaign_transition_approval_policy import (
    CampaignTransitionApprovalCategory,
    CampaignTransitionApprovalPolicy,
)


def _proposal(transition_type, risk=CampaignStateTransitionRisk.MEDIUM, approval_required=True, **kwargs):
    return CampaignStateTransitionProposal(
        proposal_id="p1",
        campaign_id="lmop",
        scene_id="scene",
        transition_type=transition_type,
        title="Proposal",
        summary="Summary",
        risk=risk,
        approval_required=approval_required,
        **kwargs,
    )


def test_policy_allows_low_risk_bookkeeping_as_auto_safe():
    policy = CampaignTransitionApprovalPolicy()
    proposal = _proposal(
        CampaignStateTransitionType.SCENE_ENTERED,
        risk=CampaignStateTransitionRisk.LOW,
        approval_required=False,
    )

    decision = policy.decide(proposal)

    assert decision.category == CampaignTransitionApprovalCategory.AUTO_SAFE
    assert decision.can_auto_apply is True
    assert decision.approval_required is False


def test_policy_requires_dm_approval_for_encounters_traps_treasure_and_xp():
    policy = CampaignTransitionApprovalPolicy()
    for transition_type in [
        CampaignStateTransitionType.ENCOUNTER_SUGGESTED,
        CampaignStateTransitionType.TRAP_DETECTED,
        CampaignStateTransitionType.TREASURE_DISCOVERED,
        CampaignStateTransitionType.XP_AWARD_CANDIDATE,
    ]:
        decision = policy.decide(_proposal(transition_type))
        assert decision.category == CampaignTransitionApprovalCategory.DM_APPROVAL_REQUIRED
        assert decision.approval_required is True


def test_policy_never_auto_for_branch_selected_and_irreversible_risk():
    policy = CampaignTransitionApprovalPolicy()

    branch = policy.decide(_proposal(CampaignStateTransitionType.BRANCH_SELECTED, risk=CampaignStateTransitionRisk.HIGH))
    irreversible = policy.decide(_proposal(CampaignStateTransitionType.SCENE_COMPLETED, risk=CampaignStateTransitionRisk.IRREVERSIBLE))

    assert branch.category == CampaignTransitionApprovalCategory.NEVER_AUTO
    assert irreversible.category == CampaignTransitionApprovalCategory.NEVER_AUTO
    assert branch.blocking_reasons
    assert irreversible.blocking_reasons


def test_policy_never_auto_for_state_mutation_preview_and_danger_tags():
    policy = CampaignTransitionApprovalPolicy()
    state_mutation = _proposal(
        CampaignStateTransitionType.TREASURE_AWARDED,
        state_patch_preview={"award_treasure": True},
    )
    dangerous_tag = _proposal(
        CampaignStateTransitionType.SCENE_COMPLETED,
        tags=["player-death"],
    )

    assert policy.decide(state_mutation).category == CampaignTransitionApprovalCategory.NEVER_AUTO
    assert policy.decide(dangerous_tag).category == CampaignTransitionApprovalCategory.NEVER_AUTO


def test_policy_batch_summary_counts_categories():
    policy = CampaignTransitionApprovalPolicy()
    batch = policy.decide_batch([
        _proposal(CampaignStateTransitionType.SCENE_ENTERED, risk=CampaignStateTransitionRisk.LOW, approval_required=False),
        _proposal(CampaignStateTransitionType.ENCOUNTER_SUGGESTED),
        _proposal(CampaignStateTransitionType.BRANCH_SELECTED, risk=CampaignStateTransitionRisk.HIGH),
    ])

    assert batch.all_auto_safe is False
    assert batch.requires_dm_approval is True
    assert batch.has_never_auto is True
    assert "1 auto-safe" in batch.summary
    assert "1 require DM approval" in batch.summary
    assert "1 never-auto" in batch.summary
