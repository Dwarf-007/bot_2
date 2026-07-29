# G1.6 – CampaignStateTransition Aggregate Gate Architecture

## Role

```text
G1.5 Runtime Wiring Smoke
Proposal generation contract
Approval policy contract
TurnOutput contract
Never-auto contract
Runtime/state-mutation scans
    -> CampaignStateTransitionAggregateGate
```

## Closure

Passing this gate means G1 can prepare state transition proposals, classify approval requirements, and render DM-facing TurnOutput without applying campaign state changes.

## Next layer

```text
G2 CampaignStateStore
```

G2 should only apply approved proposals and should preserve auditability.
