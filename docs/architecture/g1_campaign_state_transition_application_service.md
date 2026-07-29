# G1.4 – CampaignStateTransition Application Service Architecture

## Role

```text
CampaignContentAdvice / ProposalResult
    -> CampaignStateTransitionProposalService
    -> CampaignTransitionApprovalPolicy
    -> CampaignStateTransitionApplicationService
    -> TurnOutput
```

## Output separation

```text
public_narrative
    player-safe transition summary
    approval status notice

dm_instructions
    proposal evidence
    approval category
    risk
    state patch preview
    next steps

debug_notes
    diagnostics

suggested_commands
    []
```

## Automation philosophy

G1.4 prepares state transition decisions for a DM approval loop, but does not apply campaign mutations. Actual application belongs to later G2/G3 state store/orchestrator layers.
