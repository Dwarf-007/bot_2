# G1.1 – Campaign State Transition Models Architecture

## Role

```text
F3 CampaignContentAdvice
    -> G1 CampaignStateTransitionProposal
    -> DM approval
    -> later G2/G3 state application
```

## Layer responsibility

G1.1 defines only proposal models. It does not apply transitions.

## Why shared?

The same state transition proposal mechanism can serve:

```text
Campaign module progression
Donjon room progression
Sandbox NPC/quest/faction progression
Combat outcome progression
```

## Approval model

Risk and approval fields are explicit:

```text
risk
approval_required
approval_status
requires_human_review
```

This supports the long-term goal: more automated campaign running, but with human/DM approval where full automation would be brittle or unsafe.

## Later layers

```text
G1.2 ProposalService
G1.3 ApprovalPolicy
G1.4 ApplicationService / TurnOutput Mapper
G1.5 Runtime Wiring Smoke
G1.6 Aggregate Gate
G2 CampaignStateStore
G3 CampaignRuntimeOrchestrator
```
