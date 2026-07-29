# G2.4 – Campaign State Query Service Architecture

## Role

```text
CampaignStateStore
    -> CampaignStateQueryService
    -> Runtime context assembly
```

Optional existing repository context is read-only:

```text
CampaignProgressRepository
LocationRepository
RoomAliasRepository
CampaignRepository
```

The service prepares state context for later G3 runtime orchestration.
