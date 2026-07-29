# F1 – 5etools / Compendium Storage Layout

## Recommended layout

```text
data/
  compendium/
    fiveetools/
      raw/
        monsters/
          *.json
        spells/
          *.json
        items/
          *.json
        classes/
          *.json
        backgrounds/
          *.json
        feats/
          *.json
        conditions/
          *.json
        rules/
          *.json
        books/
          *.json
        adventures/
          *.json
      normalized/
      index/
```

## F1.3 behavior

`FiveEToolsDataSource` reads from:

```text
data/compendium/fiveetools/raw/
```

It accepts either files shaped as:

```json
{
  "monster": [
    {"name": "Goblin", "source": "MM"}
  ]
}
```

or list files inside type-specific folders, for example:

```text
data/compendium/fiveetools/raw/monsters/custom.json
```

with JSON:

```json
[
  {"name": "Skeleton", "source": "MM"}
]
```

## Policy reminder

The compendium layer should be used for lookup, short summaries, references,
level-up assistance, character creation assistance, and module context. It should
not reproduce long copyrighted passages or act as an authoritative rules engine.
