# F1.4 – CompendiumIndexService Architecture

## Role

`CompendiumIndexService` is the first canonical lookup/ranking service above raw compendium data sources.

```text
FiveEToolsDataSource
    -> CompendiumEntry[]
    -> CompendiumIndexService
    -> exact / alias / contains / filtered search
```

## Search strategy in F1.4

The index is intentionally simple and deterministic:

```text
1. exact name      score 1.00
2. exact alias     score 0.95
3. name prefix     score 0.85
4. name contains   score 0.75
5. alias prefix    score 0.70
6. alias contains  score 0.65
7. tag match       score 0.55
8. summary match   score 0.40
9. token subset    score 0.60
```

## Source policy

Filtering can be applied by:

```text
CompendiumQuery.allowed_sources
CompendiumQuery.rules_version
CompendiumQuery.include_homebrew
```

or by passing an explicit `SourcePolicy`.

## Later improvements

Possible later improvements:

```text
persistent generated index under data/compendium/fiveetools/index/
alias manifest
source manifest
advanced fuzzy score
RAG/embedding search
module-aware filtering
campaign source policy
```
