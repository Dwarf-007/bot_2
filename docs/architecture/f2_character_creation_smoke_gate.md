# F2.2 – CharacterCreationAdvisor Smoke Gate Architecture

## Role

```text
fixture raw data
    -> FiveEToolsDataSource
    -> CompendiumIndexService
    -> CharacterOptionService / SpellReferenceService / RulesReferenceService
    -> CharacterCreationAdvisor
    -> CharacterCreationSmokeGate
```

## Runtime coupling guard

Forbidden markers:

```text
dispatch_commands
AvraeDispatcher(
AvraeClient(
.is_available()
message.channel.send
```

## Production-like mode

The CLI can run against real copied 5etools data:

```bash
python scripts/run_character_creation_smoke.py --raw-root data/compendium/fiveetools/raw
```
