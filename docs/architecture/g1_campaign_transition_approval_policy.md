# G1.3 – Campaign Transition Approval Policy Architecture

## Role

```text
CampaignStateTransitionProposalResult
    -> CampaignTransitionApprovalPolicy
    -> CampaignTransitionApprovalBatchDecision
```

## Design goal

Support automated campaign running without unsafe hidden state mutation.

## Categories

```text
AUTO_SAFE
DM_APPROVAL_REQUIRED
NEVER_AUTO
```

## Conservative default

Only low-risk bookkeeping is auto-safe. Encounter starts, trap resolution, reward assignment, treasure awards, NPC secret reveals, and branch selection require approval or are never-auto.

## Later layers

```text
G1.4 ApplicationService / TurnOutput Mapper
G1.5 Runtime Wiring Smoke
G1.6 Aggregate Gate
G2 CampaignStateStore
G3 CampaignRuntimeOrchestrator
```
