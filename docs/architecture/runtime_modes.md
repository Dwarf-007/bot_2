# Runtime Modes Architecture

## Purpose

This document defines the runtime mode separation for the AI Dungeon Master platform. The project is not only a dungeon renderer or a Discord bot. It is a Discord-based, play-by-post AI Dungeon Master platform that can run structured dungeons, source-based campaigns, sandbox worlds, and hybrid combinations.

## Platform Goal

The platform should support:

- Discord-based asynchronous play-by-post sessions.
- Campaign material imported from official or fanmade D&D PDFs.
- Procedurally generated dungeons, especially Donjon-derived bundles.
- Sandbox play where no fixed map exists, or where the world emerges during play.
- Avrae integration for character sheets, rolls, initiative, HP, spells, and combat handoff.
- RAG-based campaign knowledge.
- Player-safe narration and spoiler-safe information exposure.
- Persistent runtime state across bot restarts.

## High-level Runtime Layers

```text
AI DM Platform
├── Core Runtime
├── Campaign Mode
├── Dungeon Mode
├── Sandbox Mode
├── Hybrid Mode
└── Avrae Integration Layer
```

## Core Runtime

Core Runtime contains components that are useful in every mode.

Responsibilities:

- Discord channel/session state.
- Campaign/session state.
- Player and party state.
- Event bus.
- Memory system.
- Runtime health diagnostics.
- LLM provider routing.
- Prompt construction.
- Story engine orchestration.
- RAG runtime interface.
- Persistence/repository layer.
- Avrae integration interface.
- Admin/debug commands.

Core Runtime must not depend directly on Donjon, TSV grids, map images, corridor visibility, or line-of-sight calculations.

## Dungeon Mode

Dungeon Mode is active when the runtime has a structured dungeon source.

Typical sources:

- Donjon JSON export.
- Donjon TSV map.
- Generated campaign bundle.
- Dungeon graph.
- Room data.
- Corridor visibility graph.
- Player map image.
- Fog manifest / map geometry.

Responsibilities:

- Room/segment/cell-level movement.
- Dungeon graph navigation.
- Corridor visibility.
- True LOS / hybrid FOV.
- Fog-of-war map rendering.
- Secret door discovery.
- Trap discovery and trap consequences.
- Local viewport rendering.
- Player-safe visibility labels.

Dungeon Mode can be playable in simplified form even when full FOW is disabled, for example when the party has received a full map from an NPC or external source.

## Campaign Mode

Campaign Mode is active when the runtime primarily follows source material.

Typical sources:

- Official D&D PDF.
- Fanmade PDF.
- User-provided campaign notes.
- RAG chunks.
- TOC/index data.
- Extracted scenes, rooms, NPCs, factions, quests, and encounters.

Responsibilities:

- Source-faithful narration.
- RAG-based retrieval.
- Spoiler-safe player-facing answers.
- Campaign progress tracking.
- Scene and quest state tracking.
- NPC/faction/plot consistency.

Campaign Mode must not require a cell grid, map image, or LOS engine. Some campaign sources may contain no usable dungeon map.

## Sandbox Mode

Sandbox Mode is active when the world is not fully pre-authored.

Typical sources:

- AI-generated locations.
- AI-generated NPCs.
- AI-generated factions.
- AI-generated quests.
- Previously persisted world state.
- Player decisions.
- DM-approved generated facts.

Responsibilities:

- Dynamic world generation.
- Persistent world state.
- Location discovery.
- NPC and faction creation.
- Quest generation.
- Consistency enforcement.
- Knowledge-fog rather than cell-level map fog.

Sandbox Mode should not require a map. In Sandbox Mode, fog-of-war usually means what locations, routes, rumors, regions, factions, and dangers are known to the party, not which cells are visible on an image.

## Hybrid Mode

Hybrid Mode is active when multiple source types are available.

Examples:

- PDF campaign with Donjon-generated side dungeon.
- Donjon dungeon with RAG-based lore.
- Sandbox overworld with generated dungeon instances.
- Campaign module where missing maps are generated procedurally.

Hybrid Mode should delegate to the most specific runtime subsystem for each player intent.

Example:

```text
Player: "I go north."
If current scene has Dungeon Mode bundle:
  use Dungeon Runtime movement.
Else if current scene has Campaign room graph:
  use Campaign Runtime navigation.
Else:
  use Sandbox Runtime world continuation.
```

## Runtime Mode Detection

A future `RuntimeModeService` should determine mode per channel/campaign.

Suggested inputs:

- `campaign_id`
- `channel_id`
- `bundle_available`
- `rag_available`
- `map_available`
- `visibility_available`
- `sandbox_enabled`
- `avrae_enabled`

Suggested output:

```text
DUNGEON
CAMPAIGN
SANDBOX
HYBRID
UNKNOWN
```

## Initial Decision

For Sprint 10, use channel-level shared party runtime state. Per-player fog-of-war and per-player private map memories are deferred.

```text
Initial state scope: channel + campaign
Deferred state scope: channel + campaign + player
```
