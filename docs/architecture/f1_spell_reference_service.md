# F1.7 – SpellReferenceService Architecture

## Role

`SpellReferenceService` is a spell-specific advisory lookup facade over `CompendiumIndexService`.

```text
FiveEToolsDataSource
    -> CompendiumEntry[]
    -> CompendiumIndexService
    -> SpellReferenceService
```

## Input scope

Primary input:

```text
data/compendium/fiveetools/raw/spells/spells-*.json
```

## Output scope

The service returns:

```text
SpellReferenceResult
    query
    found
    matches[]
    advisory_text
```

Each match carries:

```text
name
source/page/rules_version
level/school
casting_time/range/duration/components
classes, if available
score/match_reason
short snippet
```

## Policy

Use this for short spell lookup and advisory support. Do not use it as an authoritative spell execution engine or to reproduce long spell text.
