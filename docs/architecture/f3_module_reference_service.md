# F3.1 – ModuleReferenceService Architecture

## Role

```text
FiveEToolsDataSource
    -> CompendiumEntry[]
    -> CompendiumIndexService
    -> ModuleReferenceService
```

## Strategic direction

The service is part of the path toward automated campaign running. However, the design assumes that full automation is not always worth the complexity or risk.

Therefore, module lookup returns:

```text
short context snippets
dm_review_recommended
requires_dm_review per match
automation_hint per match
```

## Runtime use cases

```text
DM asks: what is in this room?
Donjon runtime asks: what reference context matches this location?
Sandbox runtime asks: what module-like context can enrich this scene?
Campaign runtime asks: what chapter/section/location should be considered next?
```

## Safety / scope

The service does not reveal long adventure text and does not make irreversible campaign state decisions. It can prepare the next step, but the DM/application layer should approve hidden or state-changing information.

## Later layers

```text
F3.2 ModuleReferenceApplicationService / TurnOutputMapper
F3.3 CampaignContentAdvisor
F3.4 Runtime context bridge
F3.5 Aggregate Gate
```
