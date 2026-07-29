# Legacy Audit

## Purpose

This document tracks components that may be active, legacy-compatible, duplicated, deprecated, or candidates for later removal.

Status values:

```text
ACTIVE
ACTIVE_LEGACY_COMPAT
DEPRECATED
REMOVE_LATER
UNKNOWN
```

## Initial Audit Summary

This is a Sprint 10 starting audit. It should be updated after code-level review and smoke tests.

## Bot Entrypoints

### `bot_core.py`

Status: `UNKNOWN`

Notes:

- Appears to be a top-level bot entry/wiring file.
- Needs comparison with `bot/bot_core.py` and `bot_core2.py`.

Action:

```text
Identify whether this is actively used by main.py, deployment scripts, or systemd service.
```

### `bot/bot_core.py`

Status: `UNKNOWN`

Notes:

- May be the package-scoped newer bot core.
- Needs import/use audit.

Action:

```text
Search imports and runtime entrypoints.
```

### `bot_core2.py`

Status: `UNKNOWN`

Notes:

- Naming suggests experimental or transitional file.
- Likely candidate for deprecation if unused.

Action:

```text
Confirm whether any active entrypoint imports this file.
If unused, mark DEPRECATED then REMOVE_LATER.
```

## LLM Components

### `llm/gemini_client.py`

Status: `UNKNOWN`

Notes:

- Likely intended package location for Gemini client.
- `app/bootstrap.py` imports `GeminiClientService` from `llm.gemini_client`, which suggests active status.

Recommended status after confirmation:

```text
ACTIVE
```

### `services/gemini_client.py`

Status: `UNKNOWN`

Notes:

- Possible legacy duplicate of `llm/gemini_client.py`.

Action:

```text
Compare public class names and imports.
If no active imports remain, mark DEPRECATED.
```

### `llm/llm_response_parser.py`

Status: `UNKNOWN`

Notes:

- `app/bootstrap.py` imports `LLMResponseParser` from this file, so likely active.

Recommended status after confirmation:

```text
ACTIVE
```

### `services/llm_response_parser.py`

Status: `UNKNOWN`

Notes:

- Possible legacy duplicate of parser logic.

Action:

```text
Compare with llm/llm_response_parser.py.
Keep one canonical parser location.
```

## Avrae Components

### `avrae/avrae_parser.py`

Status: `UNKNOWN`

Notes:

- `app/bootstrap.py` imports `AvraeParserService` from this file, so likely active.

Recommended status after confirmation:

```text
ACTIVE
```

### `services/avrae_parser.py`

Status: `UNKNOWN`

Notes:

- Possible older service-level parser.

Action:

```text
Verify active imports.
If duplicate, mark deprecated or make it a compatibility wrapper.
```

### `avrae/avrae_command_builder.py`

Status: `UNKNOWN`

Notes:

- Package-level Avrae command builder.

Action:

```text
Compare with services/avrae_command_builder.py.
```

### `services/avrae_command_builder.py`

Status: `UNKNOWN`

Notes:

- Possible older service-level command builder.

Action:

```text
Select one canonical Avrae command builder location.
```

## Dungeon / Movement Components

### `services/dungeon_master.py`

Status: `ACTIVE_LEGACY_COMPAT`

Role:

```text
High-level room graph helper, route lookup, legacy-compatible movement helper, debug utility.
```

Not responsible for:

```text
Modern cell/segment Dungeon Mode movement.
Persistent FOW.
True LOS.
Map rendering.
```

Recommended boundary:

```text
Keep as stateless high-level room/navigation helper.
Do not allow this service to become authoritative for modern Dungeon Mode position state.
```

### `services/movement_service.py`

Status: `UNKNOWN`

Notes:

- Core/legacy movement orchestration service.
- Must be reviewed against `RuntimeVisibilityMovementAdapter` and `VisibilityAwareMovementEngine`.

Action:

```text
Decide whether MovementService delegates to runtime mode handlers or remains legacy campaign-room movement.
```

### `services/movement/visibility_aware_movement_engine.py`

Status: `ACTIVE`

Role:

```text
Modern Dungeon Mode movement with visibility awareness.
```

Action:

```text
Ensure this remains the authoritative movement engine for structured dungeons.
```

### `services/visibility/visibility_engine.py`

Status: `ACTIVE`

Role:

```text
Corridor/segment visibility and visible cell calculation.
```

Action:

```text
Add or delegate Persistent FOW updates through FogOfWarPolicy.
```

### `services/runtime_visibility_movement_adapter.py`

Status: `ACTIVE`

Role:

```text
Bridge between player text intents and visibility runtime.
```

Risk:

```text
Currently owns too many responsibilities.
```

Recommended action:

```text
Extract state load/save/init/migration into RuntimeVisibilityStateService.
```

### `services/runtime_visibility_map_service.py`

Status: `ACTIVE`

Role:

```text
Runtime map rendering service for channel-specific Dungeon Mode maps.
```

Recommended action:

```text
Update to pass both visible_cells and explored_cells to renderer.
```

## State Files

### `visibility_runtime_state_<channel_id>.json`

Status: `ACTIVE`

Role:

```text
Channel-level shared party visibility state.
```

Recommended action:

```text
Add explored_cells and visited_cells with backward-compatible migration.
```

### `visibility_runtime_state_last.json`

Status: `ACTIVE_LEGACY_COMPAT`

Risk:

```text
Can become misleading in multi-channel or multi-campaign scenarios.
```

Recommended action:

```text
Keep only as debug/legacy fallback during migration.
Avoid using it as authoritative runtime state.
```

## Sprint 10 Audit Tasks

1. Search imports for all duplicate components.
2. Mark active entrypoints.
3. Identify deployment entrypoint.
4. Mark unused duplicate files as deprecated.
5. Avoid deletion in Sprint 10 unless tests prove safety.
6. Update this document after smoke test results.

## Deletion Policy

Do not delete questionable files during Sprint 10 unless all are true:

```text
- No active imports.
- No tests depend on the file.
- No deployment/script entrypoint depends on the file.
- Replacement is documented.
- Smoke tests pass.
```

Recommended approach:

```text
Sprint 10: document and deprecate.
Sprint 11+: remove or consolidate.
```
