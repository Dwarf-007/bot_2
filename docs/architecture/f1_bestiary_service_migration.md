# F1.5 – BestiaryService Migration Architecture

## Before F1.5

```text
CombatSessionService
    -> BestiaryService
        -> data/bestiary.json
```

## After F1.5

```text
CombatSessionService
    -> BestiaryService
        -> CompendiumIndexService      optional preferred path
        -> legacy data/bestiary.json   fallback compatibility path
```

## Why facade?

The combat runtime should not need to know whether monster data came from:

```text
data/bestiary.json
5etools raw JSON
normalized compendium entry
future homebrew provider
```

The public API remains:

```python
get_monster_stats(name)
```

## Later direction

Eventually the old `data/bestiary.json` path can become a generated compatibility artifact or be retired after all callers use compendium services directly.
