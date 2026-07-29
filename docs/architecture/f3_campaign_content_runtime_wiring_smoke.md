# F3.5 – CampaignContent Runtime Wiring Smoke Architecture

## Role

```text
raw adventure/book data
    -> FiveEToolsDataSource
    -> CompendiumIndexService
    -> ModuleReferenceService
    -> CampaignContentAdvisor
    -> CampaignContentApplicationService
    -> TurnOutput
```

## Smoke paths

```text
campaign_scene_turn_output      -> Goblin Ambush
Donjon room/trap TurnOutput     -> Trapped Hall
Sandbox NPC context TurnOutput  -> Important NPCs
Missing scene TurnOutput        -> Unknown Scene
```

## Runtime contract

```text
public_narrative not empty
dm_instructions present
suggested_commands == []
avrae_commands == []
```

## Automation philosophy

The smoke validates that campaign content can be prepared for runtime use while leaving hidden information and state-changing decisions behind approval checkpoints.
