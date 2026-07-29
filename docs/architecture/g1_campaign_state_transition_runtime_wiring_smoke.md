# G1.5 – CampaignStateTransition Runtime Wiring Smoke Architecture

## Role

```text
raw adventure/book data
    -> FiveEToolsDataSource
    -> CompendiumIndexService
    -> ModuleReferenceService
    -> CampaignContentAdvisor
    -> CampaignStateTransitionProposalService
    -> CampaignTransitionApprovalPolicy
    -> CampaignStateTransitionApplicationService
    -> TurnOutput
```

## Smoke paths

```text
Campaign Goblin Ambush -> encounter / branch / XP transition review
Donjon Trapped Hall -> trap transition review
Sandbox Important NPCs -> NPC info transition review
Missing Scene -> DM_REVIEW_REQUIRED
Never-auto branch -> NEVER_AUTO policy enforcement
```

## Runtime contract

```text
public_narrative not empty
dm_instructions present
suggested_commands == []
avrae_commands == []
```

## Automation philosophy

G1.5 validates that the system can prepare campaign state transition proposals for DM approval, but no transition is applied automatically.
