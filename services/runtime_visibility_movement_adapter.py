"""
SERVICES/RUNTIME_VISIBILITY_MOVEMENT_ADAPTER.PY

Sprint 10.6 update:
- Thin adapter/coordinator.
- Concrete command handling moved to RuntimeVisibilityCommandHandler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from services.runtime_campaign_bundle_resolver import RuntimeCampaignBundleResolver
from services.runtime_visibility_command_handler import RuntimeVisibilityCommandHandler
from services.runtime_visibility_intents import RuntimeVisibilityIntentParser
from services.runtime_visibility_state_service import RuntimeVisibilityStateService
from services.visibility_runtime_formatter import VisibilityRuntimeFormatter


class RuntimeVisibilityMovementAdapter:
    """Thin adapter between GameTurnService/MovementService and runtime visibility handlers."""

    def __init__(self, campaign_repo: Any = None, project_root: str | Path = ".") -> None:
        self.resolver = RuntimeCampaignBundleResolver(campaign_repo=campaign_repo, project_root=project_root)
        self.intent_parser = RuntimeVisibilityIntentParser()
        self.formatter = VisibilityRuntimeFormatter()
        self.state_service = RuntimeVisibilityStateService()
        self.command_handler = RuntimeVisibilityCommandHandler(state_service=self.state_service, formatter=self.formatter)

    def try_handle(self, *, channel_id: str, player_id: str, campaign_id: str, text: str) -> Optional[Dict[str, Any]]:
        intent = self.intent_parser.parse(text)
        if intent.kind == "NONE":
            return None

        bundle = self.resolver.resolve(campaign_id)
        if not bundle or not bundle.visibility_available:
            return None

        try:
            return self.command_handler.handle(bundle=bundle, channel_id=channel_id, player_id=player_id, intent=intent)
        except Exception as exc:
            return {
                "handled": True,
                "ok": False,
                "text": f"A visibility runtime hibát jelzett: {exc}",
                "raw": {"error": str(exc)},
            }
