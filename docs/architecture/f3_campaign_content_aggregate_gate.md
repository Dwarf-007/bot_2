# F3.6 – CampaignContent Aggregate Gate Architecture

## Role

```text
F3.5 CampaignContentRuntimeWiringSmoke
Application TurnOutput contract check
Player-safe / DM-only separation check
Approval checkpoint contract check
Runtime coupling scan
    -> CampaignContentAggregateGate
```

## TurnOutput contract

```text
public_narrative contains campaign advisory content
dm_instructions present
debug_notes present
suggested_commands == []
avrae_commands == []
```

## Player-safe / DM-only separation

The aggregate verifies that the player-facing narrative only summarizes context and warns that DM approval is required, while detailed hints remain in `dm_instructions`.

## Closure

Passing this gate means the F3 Campaign Content Foundation is stable enough to be used as an advisory runtime capability.
