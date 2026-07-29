# Fog-of-War Model

## Purpose

This document defines the persistent fog-of-war model for Dungeon Mode and separates it from Campaign/Sandbox knowledge fog.

The current runtime already has `visible_cells`, `visited_rooms`, and `visited_segments`. Sprint 10 introduces the missing persistent cell-level memory: `explored_cells`, and optionally `visited_cells`.

## Core Concepts

Dungeon Mode should distinguish at least three different cell concepts.

```text
visible_cells
  Cells the party can currently see after the latest visibility calculation.

explored_cells
  Cells the party has seen at least once in the past.

visited_cells
  Cells the party has physically occupied or traversed.
```

These are not equivalent.

Example:

```text
A character looks into a room through a doorway.
- The visible part of the room enters visible_cells.
- The same cells are added to explored_cells.
- visited_cells does not change unless the character physically enters those cells.
```

## Fog States

Minimum supported states:

```text
UNKNOWN
EXPLORED
VISIBLE
CURRENT
```

### UNKNOWN

The party has never seen the cell.

Rendering recommendation:

```text
Strong black or near-black fog overlay.
```

### EXPLORED

The party has seen the cell before, but the cell is not currently visible.

Rendering recommendation:

```text
Dimmed/desaturated/gray map visibility.
```

### VISIBLE

The party can currently see the cell.

Rendering recommendation:

```text
Bright/full-color map visibility.
```

### CURRENT

The party's current anchor or current cell.

Rendering recommendation:

```text
Visible cell plus marker/highlight.
```

## Required VisibilityState Fields

Recommended extension for `models/corridor_visibility_models.py`:

```python
visible_cells: List[Cell]
explored_cells: List[Cell]
visited_cells: List[Cell]
```

Backward-compatible migration:

```text
If explored_cells is missing:
  explored_cells = visible_cells

If visited_cells is missing and current.cell exists:
  visited_cells = [current.cell]
```

## Update Rules

After each movement or look refresh:

```text
1. Recalculate visible_cells from current position and active vision policy.
2. explored_cells = explored_cells ∪ visible_cells.
3. If current.cell exists, visited_cells = visited_cells ∪ {current.cell}.
4. Save state.
```

Important invariant:

```text
explored_cells must be monotonic during normal play.
```

That means explored cells should not disappear when the party moves away.

## Room Visibility Policy

Entering a room raises a key design question:

```text
Does the party see the whole room immediately, or only a limited area?
```

This must be policy-driven, not hardcoded.

Suggested room policies:

```text
FULL_ROOM
LIGHT_LIMITED
LOS_LIMITED
HYBRID
```

### FULL_ROOM

The full room becomes visible on entry.

Use cases:

- Small rooms.
- Simplified Donjon MVP.
- Fast play-by-post flow.
- Cases where the party has a map or the room is trivially observable.

### LIGHT_LIMITED

The room is visible only within the active vision profile.

Use cases:

- Large rooms.
- Darkness.
- Torch/darkvision rules.

### LOS_LIMITED

Only cells with true line of sight from the current anchor are visible.

Use cases:

- Pillars.
- Corners.
- Irregular geometry.
- Tactical exploration.

### HYBRID

Recommended long-term default.

Suggested behavior:

```text
Small rooms:
  FULL_ROOM

Large chambers:
  LIGHT_LIMITED + LOS_LIMITED

Corridors:
  LOS_LIMITED

Around corners:
  Not visible until the party reaches the corner or has valid LOS.

Behind closed doors:
  Not visible.

Secret doors:
  Not visible until discovered.

Traps:
  Not visible until discovered, triggered, or revealed by DM/debug mode.
```

## Dungeon Mode FOW vs Sandbox Knowledge Fog

Dungeon Mode uses cell-level FOW.

Sandbox and Campaign modes may not have cells. For these modes, use knowledge fog:

```text
known_locations
visited_locations
known_routes
rumored_locations
known_regions
known_npcs
known_factions
```

The same user-facing principle applies:

```text
The player should only receive information the party could reasonably know.
```

But the representation is not necessarily map-based.

## Initial Sprint 10 Policy Decision

Recommended initial implementation:

```text
Channel-level shared party FOW.
Small rooms can use FULL_ROOM.
Corridors use LOS/kink-limited visibility.
Large rooms should be prepared for LIGHT_LIMITED/LOS_LIMITED.
Per-player FOW is deferred.
```
