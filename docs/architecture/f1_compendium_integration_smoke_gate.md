# F1.9 – Compendium Integration Smoke Gate Architecture

## Role

`CompendiumIntegrationSmokeGate` is a dependency-light aggregate check for the compendium stack.

```text
fixture raw data
    -> FiveEToolsDataSource
    -> CompendiumIndexService
    -> BestiaryService / RulesReferenceService / SpellReferenceService / CharacterOptionService
    -> LevelUpAdvisor
```

## Runtime coupling check

The gate prevents accidental coupling of the compendium/reference layer to combat or Discord runtime concerns.

Forbidden markers:

```text
dispatch_commands
AvraeDispatcher(
AvraeClient(
.is_available()
message.channel.send
```

## Production use

The script can run against real data:

```bash
python scripts/run_compendium_integration_smoke.py --raw-root data/compendium/fiveetools/raw
```

The fixture mode remains useful in CI because it does not require large data files.
