# F1.6 – RulesReferenceService Architecture

## Role

`RulesReferenceService` is an advisory lookup facade over `CompendiumIndexService`.

```text
FiveEToolsDataSource
    -> CompendiumEntry[]
    -> CompendiumIndexService
    -> RulesReferenceService
```

## Input scope

Primary F1.6 JSON inputs:

```text
conditionsdiseases.json
actions.json
skills.json
senses.json
languages.json
variantrules.json
```

## Output scope

The service returns:

```text
RulesReferenceResult
    query
    found
    matches[]
    advisory_text
```

Each match is source-aware:

```text
name
entry_id
entry_type
source
page
rules_version
score
match_reason
snippet
```

## Policy

Use this service for short, contextual rules assistance. Do not use it to output long verbatim book passages.
