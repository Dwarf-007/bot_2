# F2.3 – CharacterCreationAdvisor Application Service Architecture

## Role

```text
Application / Runtime intent
    -> CharacterCreationApplicationRequest
    -> CharacterCreationApplicationService
    -> CharacterCreationAdvisor
    -> CharacterCreationTurnOutputMapper
    -> TurnOutput
```

## Why TurnOutput?

`TurnOutput` is the canonical output object used by the runtime. Mapping character creation advice into TurnOutput allows sandbox/donjon/application layers to consume it without Discord-specific dependencies.

## Output rule

```text
public_narrative      -> player/DM visible advisory summary
dm_instructions       -> DM/player finalization notes
suggested_commands    -> []
debug_notes           -> diagnostic metadata
```

## Boundary

No sheet mutation, no Avrae execution, no Discord I/O.
