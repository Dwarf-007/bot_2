# F3.4 – CampaignContentAdvisor Application Service Architecture

## Role

```text
Campaign/Sandbox/Donjon intent
    -> CampaignContentApplicationRequest
    -> CampaignContentApplicationService
    -> CampaignContentAdvisor
    -> CampaignContentTurnOutputMapper
    -> TurnOutput
```

## Output separation

```text
public_narrative
    player-safe short summary
    read-aloud candidate only as pending approval

dm_instructions
    DM-only context
    approval checkpoints
    recommended next steps

debug_notes
    diagnostics

suggested_commands
    []
```

## Automation philosophy

F3.4 prepares campaign-running decisions but does not apply them automatically. It supports automated campaign flow by making the next DM approval points explicit.
