# G1.2 – CampaignStateTransitionProposalService Architecture

## Role

```text
F3 CampaignContentAdvice
    -> G1 CampaignStateTransitionProposalService
    -> CampaignStateTransitionProposalResult
```

## Mapping

```text
read_aloud_candidates -> scene entry candidate
encounter_hints       -> encounter suggested
trap_hints            -> trap detected/resolution candidate
treasure_hints        -> treasure discovery candidate
reward_hints          -> XP/milestone candidate
development_hints     -> branch/outcome candidate
npc_hints             -> NPC information candidate
```

## Approval philosophy

G1.2 prepares state transitions but does not apply them. The generated proposals contain evidence, risk, state patch preview, player-visible summary, DM-only notes, and recommended next steps.

## Later layers

```text
G1.3 ApprovalPolicy
G1.4 ApplicationService / TurnOutput Mapper
G1.5 Runtime Wiring Smoke
G1.6 Aggregate Gate
G2 CampaignStateStore
G3 CampaignRuntimeOrchestrator
```
