# F3.2 – ModuleReference Application Service Architecture

## Role

```text
Campaign/Sandbox/Donjon intent
    -> ModuleReferenceApplicationRequest
    -> ModuleReferenceApplicationService
    -> ModuleReferenceService
    -> ModuleReferenceTurnOutputMapper
    -> TurnOutput
```

## Output separation

```text
public_narrative
    player-safe short advisory summary

dm_instructions
    DM-only reference snippet
    approval guidance
    recommended next steps

debug_notes
    diagnostics

suggested_commands
    []
```

## Automation philosophy

The service moves toward automated campaign running, but keeps human review where automation would be brittle or unsafe:

```text
hidden information
branching outcomes
traps/secrets
state-changing decisions
full encounter start
reward/XP assignment
```

## Future F3.3

`CampaignContentAdvisor` should classify module nodes into:

```text
read_aloud_candidate
dm_secret
encounter_hint
trap_hint
treasure_hint
npc_hint
development_hint
approval_required
```
