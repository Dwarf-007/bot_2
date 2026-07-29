"""
SERVICES/DUNGEON_RUNTIME_MVP_SMOKE_RUNNER.PY
Sprint 11.6 update: force campaign override and optional ChannelRepository binding.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from services.dungeon_runtime_mvp_smoke_service import DungeonRuntimeMvpSmokeResult, DungeonRuntimeMvpSmokeService
from services.dungeon_runtime_state_admin_service import DungeonRuntimeStateAdminService
from services.runtime_campaign_bundle_resolver import RuntimeCampaignBundleResolver

@dataclass
class DungeonRuntimeMvpSmokeRunResult:
    ok: bool
    campaign_id: str
    channel_id: str
    player_id: str
    bundle_available: bool
    visibility_available: bool
    before_status: Dict[str, Any]
    after_status: Dict[str, Any]
    smoke_result: Optional[DungeonRuntimeMvpSmokeResult] = None
    message: str = ""
    campaign_forced: bool = False
    channel_bound: bool = False
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["smoke_result"] = self.smoke_result.to_dict() if self.smoke_result else None
        return data
    def summary_text(self) -> str:
        lines = [f"Dungeon Runtime MVP smoke runner: {'OK' if self.ok else 'FAIL'}", f"campaign_id={self.campaign_id}", f"channel_id={self.channel_id}", f"player_id={self.player_id}", f"bundle_available={self.bundle_available}", f"visibility_available={self.visibility_available}", f"campaign_forced={self.campaign_forced}", f"channel_bound={self.channel_bound}"]
        if self.message:
            lines.append(f"message={self.message}")
        if self.smoke_result:
            lines.append("")
            lines.append(self.smoke_result.summary_text())
        return "\n".join(lines)

class DungeonRuntimeMvpSmokeRunner:
    def __init__(self, *, game_turn_service: Any, campaign_repo: Any = None, project_root: str = ".", state_admin_service: Optional[DungeonRuntimeStateAdminService] = None, resolver: Optional[RuntimeCampaignBundleResolver] = None) -> None:
        self.game_turn_service = game_turn_service
        self.resolver = resolver or RuntimeCampaignBundleResolver(campaign_repo=campaign_repo, project_root=project_root)
        self.state_admin_service = state_admin_service or DungeonRuntimeStateAdminService(campaign_repo=campaign_repo, project_root=project_root)
    def run(self, *, campaign_id: str, channel_id: str, player_id: str, reset_before: bool = False, remove_debug_mirror_on_reset: bool = False, force_campaign: bool = True, bind_channel: bool = False) -> DungeonRuntimeMvpSmokeRunResult:
        bundle = self.resolver.resolve(campaign_id)
        if not bundle:
            return DungeonRuntimeMvpSmokeRunResult(False, campaign_id, channel_id, player_id, False, False, {}, {}, None, f"Nem található runtime bundle ehhez a kampányhoz: {campaign_id}", force_campaign, False)
        visibility_available = bool(getattr(bundle, "visibility_available", False))
        if not visibility_available:
            before = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
            return DungeonRuntimeMvpSmokeRunResult(False, campaign_id, channel_id, player_id, True, False, before, before, None, "A runtime bundle létezik, de visibility_available=False.", force_campaign, False)
        channel_bound = False
        if bind_channel:
            bind = getattr(self.game_turn_service, "bind_channel_campaign_for_smoke", None)
            if bind:
                channel_bound = bool(bind(channel_id=channel_id, campaign_id=campaign_id, mode="dungeon"))
        if reset_before:
            self.state_admin_service.reset(campaign_id=campaign_id, channel_id=channel_id, player_id=player_id, remove_debug_mirror=remove_debug_mirror_on_reset)
        before_status = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
        smoke = DungeonRuntimeMvpSmokeService(self.game_turn_service).run(channel_id=channel_id, player_id=player_id, campaign_id_override=campaign_id if force_campaign else None)
        after_status = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
        return DungeonRuntimeMvpSmokeRunResult(bool(smoke.ok), campaign_id, channel_id, player_id, True, True, before_status, after_status, smoke, "Smoke run completed." if smoke.ok else "Smoke run failed.", force_campaign, channel_bound)
