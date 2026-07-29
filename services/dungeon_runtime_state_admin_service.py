"""
SERVICES/DUNGEON_RUNTIME_STATE_ADMIN_SERVICE.PY

Sprint 11.4 update:
- Adds smoke_status() helper for admin/debug layers.
- Keeps state reset/status helpers from Sprint 11.3.
"""

from __future__ import annotations

from typing import Any, Dict

from services.runtime_campaign_bundle_resolver import RuntimeCampaignBundleResolver
from services.runtime_visibility_state_service import RuntimeVisibilityStateService


class DungeonRuntimeStateAdminService:
    """Admin/debug helper around Dungeon Runtime channel state."""

    def __init__(self, *, campaign_repo: Any = None, project_root: str = ".", state_service: RuntimeVisibilityStateService | None = None) -> None:
        self.resolver = RuntimeCampaignBundleResolver(campaign_repo=campaign_repo, project_root=project_root)
        self.state_service = state_service or RuntimeVisibilityStateService(enable_legacy_last_fallback=False, write_legacy_last=True)

    def status(self, *, campaign_id: str, channel_id: str) -> Dict[str, Any]:
        bundle = self.resolver.resolve(campaign_id)
        if not bundle:
            return {"ok": False, "message": f"Nem található runtime bundle ehhez a kampányhoz: {campaign_id}"}
        files = self.state_service.describe_state_files(bundle, channel_id)
        return {
            "ok": True,
            "campaign_id": campaign_id,
            "channel_id": channel_id,
            "bundle_dir": str(bundle.bundle_dir),
            "visibility_available": bool(getattr(bundle, "visibility_available", False)),
            **files,
        }

    def reset(self, *, campaign_id: str, channel_id: str, player_id: str = "", remove_debug_mirror: bool = False) -> Dict[str, Any]:
        bundle = self.resolver.resolve(campaign_id)
        if not bundle:
            return {"ok": False, "message": f"Nem található runtime bundle ehhez a kampányhoz: {campaign_id}"}
        state = self.state_service.reset_state(bundle, channel_id=channel_id, player_id=player_id, remove_debug_mirror=remove_debug_mirror)
        return {
            "ok": True,
            "message": "Dungeon runtime state reset megtörtént.",
            "campaign_id": campaign_id,
            "channel_id": channel_id,
            "state": state.to_dict() if hasattr(state, "to_dict") else None,
            **self.state_service.describe_state_files(bundle, channel_id),
        }

    def cleanup_debug_mirror(self, *, campaign_id: str) -> Dict[str, Any]:
        bundle = self.resolver.resolve(campaign_id)
        if not bundle:
            return {"ok": False, "message": f"Nem található runtime bundle ehhez a kampányhoz: {campaign_id}"}
        deleted = self.state_service.cleanup_debug_mirror(bundle)
        return {
            "ok": True,
            "campaign_id": campaign_id,
            "deleted": deleted,
            "debug_mirror_file": str(self.state_service.legacy_last_file(bundle)),
        }

    def smoke_status(self, *, campaign_id: str, channel_id: str) -> Dict[str, Any]:
        """Return a compact status payload suitable before/after MVP smoke runs."""
        status = self.status(campaign_id=campaign_id, channel_id=channel_id)
        if not status.get("ok"):
            return status
        return {
            "ok": True,
            "campaign_id": campaign_id,
            "channel_id": channel_id,
            "visibility_available": status.get("visibility_available"),
            "authoritative_exists": status.get("authoritative_exists"),
            "debug_mirror_exists": status.get("debug_mirror_exists"),
            "authoritative_state_file": status.get("authoritative_state_file"),
            "debug_mirror_file": status.get("debug_mirror_file"),
        }
