# F3.3 – CampaignContentAdvisor Architecture

## Role

```text
ModuleReferenceService
    -> ModuleContentNode[]
    -> CampaignContentAdvisor
    -> CampaignContentAdvice
```

## Classification goals

```text
read-aloud candidate
player-visible candidate
DM secret
encounter hint
trap hint
treasure hint
NPC hint
development/outcome hint
reward/XP hint
approval checkpoint
```

## Automation philosophy

The system moves toward automated campaign running by identifying what a piece of module text is for. It does not apply state changes automatically. It prepares next-step proposals and approval checkpoints.

## Later F3.4

The next layer should map `CampaignContentAdvice` to `TurnOutput`:

```text
public_narrative      -> player-safe summary/read-aloud candidate after approval
dm_instructions       -> DM-only content and approval checkpoints
suggested_commands    -> []
debug_notes           -> diagnostics
```
