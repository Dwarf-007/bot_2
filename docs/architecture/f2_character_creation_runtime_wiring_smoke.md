# F2.4 – CharacterCreationAdvisor Runtime Wiring Smoke Architecture

## Role

```text
raw compendium data
    -> FiveEToolsDataSource
    -> CompendiumIndexService
    -> CharacterOptionService / SpellReferenceService / RulesReferenceService
    -> CharacterCreationAdvisor
    -> CharacterCreationApplicationService
    -> TurnOutput
```

## Smoke paths

```text
Donjon scout DTO payload
Sandbox frontliner dict payload
Wizard spellcaster dict payload
Incomplete request dict payload
```

## Runtime contract

Every smoke path must return:

```text
TurnOutput.public_narrative not empty
TurnOutput.dm_instructions present
TurnOutput.suggested_commands == []
TurnOutput.avrae_commands == []
```

## Boundary

No Discord I/O, no Avrae execution, no character sheet mutation.
