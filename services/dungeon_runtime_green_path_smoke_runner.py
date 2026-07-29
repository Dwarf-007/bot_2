"""
SERVICES/DUNGEON_RUNTIME_GREEN_PATH_SMOKE_RUNNER.PY

Sprint 12.4 - Real-bundle runner for DungeonRuntimeGreenPathSmokeService.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from services.dungeon_runtime_green_path_smoke_service import DungeonRuntimeGreenPathSmokeResult, DungeonRuntimeGreenPathSmokeService
from services.dungeon_runtime_state_admin_service import DungeonRuntimeStateAdminService
from services.runtime_campaign_bundle_resolver import RuntimeCampaignBundleResolver


@dataclass
class DungeonRuntimeGreenPathSmokeRunResult:
    ok: bool
    campaign_id: str
    channel_id: str
    player_id: str
    bundle_available: bool
    visibility_available: bool
    before_status: Dict[str, Any]
    after_status: Dict[str, Any]
    smoke_result: Optional[DungeonRuntimeGreenPathSmokeResult] = None
    message: str = ""
    campaign_forced: bool = True
    channel_bound: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["smoke_result"] = self.smoke_result.to_dict() if self.smoke_result else None
        return data

    def summary_text(self) -> str:
        lines = [
            f"Dungeon Runtime green-path smoke runner: {'OK' if self.ok else 'FAIL'}",
            f"campaign_id={self.campaign_id}",
            f"channel_id={self.channel_id}",
            f"player_id={self.player_id}",
            f"bundle_available={self.bundle_available}",
            f"visibility_available={self.visibility_available}",
            f"campaign_forced={self.campaign_forced}",
            f"channel_bound={self.channel_bound}",
        ]
        if self.message:
            lines.append(f"message={self.message}")
        if self.smoke_result:
            lines.append("")
            lines.append(self.smoke_result.summary_text())
        return "\n".join(lines)


class DungeonRuntimeGreenPathSmokeRunner:
    def __init__(
        self,
        *,
        game_turn_service: Any,
        campaign_repo: Any = None,
        project_root: str = ".",
        state_admin_service: Optional[DungeonRuntimeStateAdminService] = None,
        resolver: Optional[RuntimeCampaignBundleResolver] = None,
    ) -> None:
        self.game_turn_service = game_turn_service
        self.resolver = resolver or RuntimeCampaignBundleResolver(campaign_repo=campaign_repo, project_root=project_root)
        self.state_admin_service = state_admin_service or DungeonRuntimeStateAdminService(
            campaign_repo=campaign_repo,
            project_root=project_root,
        )

    def run(
        self,
        *,
        campaign_id: str,
        channel_id: str,
        player_id: str,
        reset_before: bool = False,
        bind_channel: bool = False,
        force_campaign: bool = True,
    ) -> DungeonRuntimeGreenPathSmokeRunResult:
        bundle = self.resolver.resolve(campaign_id)
        if not bundle:
            return DungeonRuntimeGreenPathSmokeRunResult(
                ok=False,
                campaign_id=campaign_id,
                channel_id=channel_id,
                player_id=player_id,
                bundle_available=False,
                visibility_available=False,
                before_status={},
                after_status={},
                smoke_result=None,
                message=f"Nem található runtime bundle ehhez a kampányhoz: {campaign_id}",
                campaign_forced=force_campaign,
                channel_bound=False,
            )
        visibility_available = bool(getattr(bundle, "visibility_available", False))
        if not visibility_available:
            before = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
            return DungeonRuntimeGreenPathSmokeRunResult(
                ok=False,
                campaign_id=campaign_id,
                channel_id=channel_id,
                player_id=player_id,
                bundle_available=True,
                visibility_available=False,
                before_status=before,
                after_status=before,
                smoke_result=None,
                message="A runtime bundle létezik, de visibility_available=False.",
                campaign_forced=force_campaign,
                channel_bound=False,
            )

        channel_bound = False
        if bind_channel:
            bind = getattr(self.game_turn_service, "bind_channel_campaign_for_smoke", None)
            if bind:
                channel_bound = bool(bind(channel_id=channel_id, campaign_id=campaign_id, mode="dungeon"))

        if reset_before:
            self.state_admin_service.reset(campaign_id=campaign_id, channel_id=channel_id, player_id=player_id)

        before_status = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
        smoke = DungeonRuntimeGreenPathSmokeService(self.game_turn_service).run(
            channel_id=channel_id,
            player_id=player_id,
            campaign_id_override=campaign_id if force_campaign else None,
        )
        after_status = self.state_admin_service.smoke_status(campaign_id=campaign_id, channel_id=channel_id)
        return DungeonRuntimeGreenPathSmokeRunResult(
            ok=bool(smoke.ok),
            campaign_id=campaign_id,
            channel_id=channel_id,
            player_id=player_id,
            bundle_available=True,
            visibility_available=True,
            before_status=before_status,
            after_status=after_status,
            smoke_result=smoke,
            message="Green-path smoke completed." if smoke.ok else "Green-path smoke failed.",
            campaign_forced=force_campaign,
            channel_bound=channel_bound,
        )
