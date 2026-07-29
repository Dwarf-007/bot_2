# G2.3 – Campaign Transition Application Service Architecture

## Role

```text
G1 approved proposal
    -> CampaignTransitionApplicationService
    -> CampaignStateStore
    -> optional CampaignProgressRepository bridge
```

## Important boundary

This service applies only approved/non-never-auto proposals. It does not render TurnOutput and does not interact with Discord or Avrae.

## Repository compatibility

Optional hooks align with existing repository APIs:

```text
CampaignProgressRepository.set_channel_progress
CampaignProgressRepository.add_objective
```

Later versions can add deeper adapters for CampaignRepository, LocationRepository, and RoomAliasRepository.
