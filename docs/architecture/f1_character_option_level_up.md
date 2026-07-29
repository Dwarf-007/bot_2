# F1.8 – CharacterOptionService / LevelUpAdvisor Architecture

## Role

```text
CompendiumIndexService
    -> CharacterOptionService
    -> LevelUpAdvisor
```

## CharacterOptionService

Used for:

```text
class lookup
subclass lookup
species lookup
background lookup
feat lookup
class feature discovery for levels
```

## LevelUpAdvisor

Used for:

```text
player-facing level-up checklist
DM-facing review points
generic HP/proficiency/resource/sheet checks
spellcasting review reminder
```

## Policy

This is an advisory helper. It does not mutate character sheets and does not act as a rules authority.
