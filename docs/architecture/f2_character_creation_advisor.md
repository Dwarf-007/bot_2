# F2.1 – CharacterCreationAdvisor Architecture

## Role

```text
CompendiumIndexService
    -> CharacterOptionService
    -> CharacterCreationAdvisor
```

Optional:

```text
RulesReferenceService
SpellReferenceService
```

## Responsibility

`CharacterCreationAdvisor` builds a DM/player-facing checklist for creating a character.

It is designed for:

```text
player character creation
sandbox NPC/sidekick/rival quick concepts
donjon/megadungeon party readiness
```

## Non-goals

```text
authoritative character sheet engine
Avrae/D&D Beyond mutation
full rules automation
LLM generation
```

## Output

```text
CharacterCreationAdvice
    selected options
    compendium lookup summaries
    missing choices
    checklist
    advisory_text
```
