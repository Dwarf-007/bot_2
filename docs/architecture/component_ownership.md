# Component Ownership

## Purpose

This document defines which layer owns which responsibilities. The goal is to avoid hidden coupling between Discord, campaign logic, dungeon movement, visibility, rendering, and AI narration.

## Ownership Principles

1. Core Runtime should not depend on Donjon-specific files.
2. Dungeon Runtime should own grid/segment/cell visibility.
3. Campaign Runtime should own source-faithful RAG behavior.
4. Sandbox Runtime should own generated world state.
5. Avrae should remain the preferred owner of character-sheet and many combat mechanics.
6. Renderers should render; they should not decide game rules.
7. State stores should store; they should not calculate visibility.
8. Engines should calculate; they should not directly own Discord output formatting.

## Core Runtime Components

Expected Core Runtime components:

```text
app/bootstrap.py
core/event_bus.py
core/game_events.py
services/game_turn_service.py
services/context_service.py
services/prompt_builder.py
services/story_engine.py
services/runtime_health_service.py
services/memory_event_service.py
services/memory_summary_service.py
repositories/*
persistence/database.py
llm/*
```

Responsibilities:

- Dependency wiring.
- Event dispatch.
- Turn orchestration.
- Prompt construction.
- LLM routing.
- Memory and context management.
- Repository/persistence operations.
- Health diagnostics.

Core Runtime should delegate mode-specific actions to mode-specific services.

## Dungeon Runtime Components

Expected Dungeon Runtime components:

```text
services/runtime_visibility_movement_adapter.py
services/runtime_visibility_map_service.py
services/visibility/visibility_engine.py
services/visibility/true_los_visibility_engine.py
services/visibility/fov_anchor.py
services/visibility/corridor_segmenter.py
services/visibility/corridor_segment_merge_engine.py
services/visibility/visibility_graph_builder.py
services/visibility/door_visibility_policy.py
services/visibility/door_metadata_binder.py
services/visibility/secret_door_discovery_engine.py
services/visibility/fog_cell_renderer.py
services/visibility/visible_cell_expander.py
services/movement/visibility_aware_movement_engine.py
services/movement/movement_engine.py
services/movement/movement_state_store.py
services/dungeons/*
```

Responsibilities:

- Structured dungeon import.
- Room/segment/cell movement.
- Current visible cell calculation.
- Persistent explored cell maintenance.
- Secret door discovery state.
- Player-safe dungeon information.
- Map image rendering.
- Local viewport generation.

## Campaign Runtime Components

Expected Campaign Runtime components:

```text
services/rag_runtime.py
repositories/rag_chunk_repository.py
services/campaign_service.py
services/progress_service.py
services/context_service.py
services/room_alias_service.py
services/prompt_builder.py
```

Responsibilities:

- Campaign source tracking.
- RAG retrieval.
- Campaign progress.
- Room/scene aliasing.
- Spoiler-safe context assembly.
- Source-faithful narration.

Campaign Mode should work even when no dungeon grid or image map exists.

## Sandbox Runtime Components

Expected future Sandbox Runtime components:

```text
models/sandbox_world_state.py
models/sandbox_location.py
models/sandbox_npc.py
models/sandbox_faction.py
services/sandbox_world_service.py
services/sandbox_location_generator.py
services/sandbox_consistency_service.py
repositories/sandbox_world_repository.py
```

Responsibilities:

- Dynamic world generation.
- World memory persistence.
- Generated location tracking.
- NPC/faction/quest state.
- Knowledge fog.
- Consistency validation.

This layer is future-facing and should not be implemented deeply in Sprint 10.

## Avrae Integration Layer

Expected Avrae components:

```text
avrae/avrae_parser.py
avrae/avrae_command_builder.py
services/avrae_parser.py
services/avrae_command_builder.py
services/combat_feedback_service.py
services/combat_start_service.py
subscribers/combat_resolution_subscriber.py
```

Responsibilities:

- Parse Avrae output.
- Build Avrae commands.
- React to combat resolution events.
- Avoid duplicating Avrae-owned character-sheet logic.

Recommended boundary:

```text
AI DM owns narration, campaign logic, world state, visibility, and player-facing explanation.
Avrae owns character sheet, rolls, initiative, HP, attacks, spells, and combat mechanics where possible.
```

## Rendering Components

Expected rendering components:

```text
services/runtime_visibility_map_service.py
services/visibility/fog_cell_renderer.py
services/dungeons/fog_of_war_renderer.py
tools/render_runtime_visibility_map.py
tools/render_fog_map.py
```

Responsibilities:

- Render map images.
- Apply fog overlay.
- Render local viewport.
- Draw current cell marker.

Renderers should receive already-decided cell states. Renderers should not decide whether a secret door is discovered or whether a trap is visible.

## State Ownership

Suggested state ownership:

```text
ChannelRepository
  Discord channel state, active campaign, current high-level state.

VisibilityStateStore
  Dungeon Mode channel-level visibility state.

SecretDiscoveryStateStore
  Secret door discovery state.

MovementStateStore
  Movement-related runtime state where separate from VisibilityState.

CampaignProgressRepository
  Campaign/source progress.

MemoryRepository
  Long-term memory and event memory.
```

Initial Sprint 10 state scope:

```text
campaign_id + channel_id
```

Deferred state scope:

```text
campaign_id + channel_id + player_id
```

## Key Architectural Risk

The main risk is parallel ownership of movement state.

Potentially overlapping components:

```text
services/dungeon_master.py
services/movement_service.py
services/movement/visibility_aware_movement_engine.py
services/visibility/visibility_engine.py
services/runtime_visibility_movement_adapter.py
```

Sprint 10 should document which component is authoritative in each mode.

Recommended decision:

```text
DungeonMasterService:
  High-level room graph helper / legacy-compatible lookup / debug route helper.

VisibilityAwareMovementEngine + CorridorVisibilityEngine:
  Authoritative Dungeon Mode movement/visibility runtime.

MovementService:
  Core or legacy movement orchestration, should delegate to mode-specific engines.
```
