
"""
SERVICES/RUNTIME_VISIBILITY_STATE_SERVICE.PY

Sprint 12.5.1 - VisibilityState raw-key compatibility hotfix.

Fixes the green-path local map issue:
- VisibilityAwareMovementEngine.look() returns updated state under raw["visibility_state"].
- RuntimeVisibilityStateService.state_from_raw() previously only accepted raw["state"].
- Therefore handle_look() could not persist refreshed visible_cells before `map`.

Now state_from_raw() accepts both:
- raw["state"]
- raw["visibility_state"]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from services.runtime_campaign_bundle_resolver import ResolvedCampaignBundle
from services.visibility.visibility_state_store import VisibilityStateStore


class RuntimeVisibilityStateService:
    """Owns channel-scoped runtime visibility state persistence."""

    def __init__(self, *, enable_legacy_last_fallback: bool = False, write_legacy_last: bool = True) -> None:
        self.enable_legacy_last_fallback = bool(enable_legacy_last_fallback)
        self.write_legacy_last = bool(write_legacy_last)

    def state_file(self, bundle: ResolvedCampaignBundle, channel_id: str) -> Path:
        safe = self.safe_scope_id(channel_id)
        return bundle.bundle_dir / f"visibility_runtime_state_{safe}.json"

    def legacy_last_file(self, bundle: ResolvedCampaignBundle) -> Path:
        return bundle.bundle_dir / "visibility_runtime_state_last.json"

    @staticmethod
    def safe_scope_id(value: str) -> str:
        return str(value).replace("/", "_").replace("\\", "_")

    def state_exists(self, bundle: ResolvedCampaignBundle, channel_id: str) -> bool:
        return self.state_file(bundle, channel_id).exists()

    def load_state(self, bundle: ResolvedCampaignBundle, channel_id: str) -> Optional[Any]:
        store = VisibilityStateStore(self.state_file(bundle, channel_id))
        loaded = store.load()
        if not loaded:
            return None
        migrated = self.migrate_state(loaded)
        store.save(migrated)
        return migrated

    def load_or_init_state(self, bundle: ResolvedCampaignBundle, channel_id: str, player_id: str = "") -> Any:
        loaded = self.load_state(bundle, channel_id)
        if loaded:
            return loaded
        if self.enable_legacy_last_fallback:
            legacy_last = self.legacy_last_file(bundle)
            if legacy_last.exists():
                loaded = VisibilityStateStore(legacy_last).load()
                if loaded:
                    migrated = self.migrate_state(loaded)
                    VisibilityStateStore(self.state_file(bundle, channel_id)).save(migrated)
                    return migrated
        return self.reset_state(bundle, channel_id=channel_id, player_id=player_id, remove_debug_mirror=False)

    def init_state(self, bundle: ResolvedCampaignBundle, *, channel_id: str = "", player_id: str = "") -> Any:
        from models.corridor_visibility_models import VisibilityPosition, VisibilityState
        start_room = self.infer_start_room(bundle, channel_id)
        state = VisibilityState(
            campaign_id=bundle.campaign_id,
            current=VisibilityPosition(
                node_id=start_room,
                node_type="room",
                level=self.level_from_room_id(start_room),
                room_id=start_room,
                segment_id=None,
                cell=None,
            ),
            visited_rooms=[start_room],
            visited_segments=[],
            visible_cells=[],
            explored_cells=[],
            visited_cells=[],
            path_history=[],
        )
        return self.migrate_state(state)

    def save_state(self, bundle: ResolvedCampaignBundle, channel_id: str, state: Any) -> None:
        migrated = self.migrate_state(state)
        VisibilityStateStore(self.state_file(bundle, channel_id)).save(migrated)
        if self.write_legacy_last:
            self.write_debug_mirror(bundle, migrated)

    def write_debug_mirror(self, bundle: ResolvedCampaignBundle, state: Any) -> None:
        try:
            VisibilityStateStore(self.legacy_last_file(bundle)).save(self.migrate_state(state))
        except Exception:
            pass

    def reset_state(self, bundle: ResolvedCampaignBundle, *, channel_id: str, player_id: str = "", remove_debug_mirror: bool = False) -> Any:
        state = self.init_state(bundle, channel_id=channel_id, player_id=player_id)
        VisibilityStateStore(self.state_file(bundle, channel_id)).save(state)
        if remove_debug_mirror:
            self.cleanup_debug_mirror(bundle)
        elif self.write_legacy_last:
            self.write_debug_mirror(bundle, state)
        return state

    def delete_state(self, bundle: ResolvedCampaignBundle, channel_id: str) -> bool:
        path = self.state_file(bundle, channel_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def cleanup_debug_mirror(self, bundle: ResolvedCampaignBundle) -> bool:
        path = self.legacy_last_file(bundle)
        if path.exists():
            path.unlink()
            return True
        return False

    def describe_state_files(self, bundle: ResolvedCampaignBundle, channel_id: str) -> Dict[str, Any]:
        authoritative = self.state_file(bundle, channel_id)
        debug = self.legacy_last_file(bundle)
        return {
            "authoritative_state_file": str(authoritative),
            "authoritative_exists": authoritative.exists(),
            "debug_mirror_file": str(debug),
            "debug_mirror_exists": debug.exists(),
            "legacy_last_fallback_enabled": self.enable_legacy_last_fallback,
            "debug_mirror_write_enabled": self.write_legacy_last,
        }

    def migrate_state(self, state: Any) -> Any:
        if not hasattr(state, "path_history") or getattr(state, "path_history", None) is None:
            try:
                state.path_history = []
            except Exception:
                pass
        if not hasattr(state, "explored_cells") or getattr(state, "explored_cells", None) is None:
            try:
                state.explored_cells = []
            except Exception:
                pass
        if not hasattr(state, "visited_cells") or getattr(state, "visited_cells", None) is None:
            try:
                state.visited_cells = []
            except Exception:
                pass
        try:
            if not getattr(state, "explored_cells", None):
                state.explored_cells = list(getattr(state, "visible_cells", []) or [])
        except Exception:
            pass
        try:
            current = getattr(state, "current", None)
            cell = getattr(current, "cell", None) if current else None
            if cell is not None and not getattr(state, "visited_cells", None):
                state.visited_cells = [tuple(cell)]
        except Exception:
            pass
        return state

    def state_from_raw(self, raw: dict[str, Any]) -> Optional[Any]:
        """Extract VisibilityState from a command raw response.

        Supported keys:
        - state: older direct state key
        - visibility_state: VisibilityAwareMovementEngine key
        """
        if not isinstance(raw, dict):
            return None
        raw_state = raw.get("state")
        if not isinstance(raw_state, dict):
            raw_state = raw.get("visibility_state")
        if not isinstance(raw_state, dict):
            return None
        from models.corridor_visibility_models import VisibilityState
        try:
            return self.migrate_state(VisibilityState.from_dict(raw_state))
        except Exception:
            return None

    def infer_start_room(self, bundle: ResolvedCampaignBundle, channel_id: str = "") -> str:
        p = bundle.bundle_dir / "visibility_state.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cur = data.get("current") or {}
                if cur.get("room_id"):
                    return str(cur["room_id"])
            except Exception:
                pass
        room_data = bundle.bundle_dir / "room_data.json"
        data = json.loads(room_data.read_text(encoding="utf-8")) if room_data.exists() else {}
        rooms = data.get("rooms") or []
        if rooms:
            for room in rooms:
                if room.get("is_entrance"):
                    return str(room.get("room_id"))
            return str(rooms[0].get("room_id"))
        return f"{bundle.campaign_id}:L01:R001"

    @staticmethod
    def level_from_room_id(room_id: str) -> int:
        import re
        m = re.search(r":L(\d+):", str(room_id))
        return int(m.group(1)) if m else 1
