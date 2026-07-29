"""
SERVICES/RUNTIME_MODE_ROUTER.PY

Sprint 11.2 update:
- Adds DungeonRuntimeMvpCommandCatalog gate before calling Dungeon Runtime.
- DUNGEON/HYBRID modes only call the visibility adapter for MVP dungeon commands.
- UNKNOWN transitional probing also respects the MVP command gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from models.runtime_mode import RuntimeMode, RuntimeModeDecision, RuntimeModeSignals, RuntimeSourceType
from services.dungeon_runtime_mvp_commands import DungeonRuntimeMvpCommandCatalog
from services.runtime_mode_service import RuntimeModeService


@dataclass(frozen=True)
class RuntimeRouteResult:
    handled: bool
    output: Optional[Dict[str, Any]] = None
    decision: Optional[RuntimeModeDecision] = None
    campaign_id: Optional[str] = None
    skipped_reason: str = ""

    def to_debug(self) -> Dict[str, Any]:
        return {
            "handled": self.handled,
            "campaign_id": self.campaign_id,
            "decision": self.decision.to_dict() if self.decision else None,
            "skipped_reason": self.skipped_reason,
        }


class RuntimeModeRouter:
    """Routes one player input according to the active runtime mode."""

    def __init__(
        self,
        *,
        runtime_mode_service: RuntimeModeService,
        visibility_movement_adapter: Any = None,
        allow_unknown_dungeon_probe: bool = True,
        dungeon_command_catalog: DungeonRuntimeMvpCommandCatalog | None = None,
    ) -> None:
        self.runtime_mode_service = runtime_mode_service
        self.visibility_movement_adapter = visibility_movement_adapter
        self.allow_unknown_dungeon_probe = bool(allow_unknown_dungeon_probe)
        self.dungeon_command_catalog = dungeon_command_catalog or DungeonRuntimeMvpCommandCatalog()

    def try_handle_pre_llm(
        self,
        *,
        channel_repo: Any,
        channel_id: str,
        player_id: str,
        campaign_id: str,
        text: str,
    ) -> RuntimeRouteResult:
        """Try deterministic mode-specific handlers before rest/legacy/LLM flow."""
        decision = self.decide_for_channel(channel_repo=channel_repo, channel_id=channel_id, campaign_id=campaign_id)

        if not self.should_try_dungeon_runtime(decision):
            return RuntimeRouteResult(False, None, decision, campaign_id, skipped_reason="mode_not_dungeon")

        if not self.dungeon_command_catalog.is_mvp_command(text):
            return RuntimeRouteResult(False, None, decision, campaign_id, skipped_reason="not_dungeon_mvp_command")

        output = self.try_dungeon_runtime(channel_id=channel_id, player_id=player_id, campaign_id=campaign_id, text=text)
        if output and output.get("handled"):
            return RuntimeRouteResult(True, output, decision, campaign_id)

        return RuntimeRouteResult(False, None, decision, campaign_id, skipped_reason="dungeon_runtime_not_handled")

    def should_try_dungeon_runtime(self, decision: RuntimeModeDecision) -> bool:
        if decision.mode in {RuntimeMode.DUNGEON, RuntimeMode.HYBRID}:
            return True
        if decision.mode == RuntimeMode.UNKNOWN and self.allow_unknown_dungeon_probe:
            return True
        return False

    def try_dungeon_runtime(self, *, channel_id: str, player_id: str, campaign_id: str, text: str) -> Optional[Dict[str, Any]]:
        if not self.visibility_movement_adapter:
            return None
        return self.visibility_movement_adapter.try_handle(
            channel_id=channel_id,
            player_id=player_id,
            campaign_id=campaign_id,
            text=text,
        )

    def decide_for_channel(self, *, channel_repo: Any, channel_id: str, campaign_id: str) -> RuntimeModeDecision:
        state = self._channel_state(channel_repo, channel_id)
        signals = self._signals_from_state(state, channel_id=channel_id, campaign_id=campaign_id)
        signals = self._merge_bundle_signals(signals, campaign_id=campaign_id)
        return self.runtime_mode_service.decide(signals)

    def _channel_state(self, channel_repo: Any, channel_id: str) -> Dict[str, Any]:
        for method_name in ("get_state", "get_channel_state", "load_state"):
            method = getattr(channel_repo, method_name, None)
            if not method:
                continue
            try:
                state = method(channel_id)
                return state if isinstance(state, dict) else {}
            except Exception:
                continue
        return {}

    def _signals_from_state(self, state: Dict[str, Any], *, channel_id: str, campaign_id: str) -> RuntimeModeSignals:
        source_type = self._source_type_from_state(state)
        explicit_mode = str(state.get("runtime_mode") or state.get("mode") or "").strip().upper()

        bundle_available = bool(state.get("bundle_available", False))
        rag_available = bool(state.get("rag_available", False) or state.get("rag_index_available", False))
        map_available = bool(state.get("map_available", False))
        visibility_available = bool(state.get("visibility_available", False))
        sandbox_enabled = bool(state.get("sandbox_enabled", False))
        avrae_enabled = bool(state.get("avrae_enabled", False))

        if explicit_mode == "DUNGEON":
            bundle_available = True
            visibility_available = True
            source_type = RuntimeSourceType.DONJON_BUNDLE if source_type == RuntimeSourceType.UNKNOWN else source_type
        elif explicit_mode == "CAMPAIGN":
            rag_available = True
            source_type = RuntimeSourceType.RAG_ONLY if source_type == RuntimeSourceType.UNKNOWN else source_type
        elif explicit_mode == "SANDBOX":
            sandbox_enabled = True
            source_type = RuntimeSourceType.SANDBOX
        elif explicit_mode == "HYBRID":
            bundle_available = True
            visibility_available = True
            rag_available = True
            source_type = RuntimeSourceType.MIXED

        return RuntimeModeSignals(
            campaign_id=campaign_id,
            channel_id=channel_id,
            source_type=source_type,
            bundle_available=bundle_available,
            rag_available=rag_available,
            map_available=map_available,
            visibility_available=visibility_available,
            sandbox_enabled=sandbox_enabled,
            avrae_enabled=avrae_enabled,
        )

    def _merge_bundle_signals(self, signals: RuntimeModeSignals, *, campaign_id: str) -> RuntimeModeSignals:
        adapter = self.visibility_movement_adapter
        resolver = getattr(adapter, "resolver", None)
        if resolver is None:
            return signals
        try:
            bundle = resolver.resolve(campaign_id)
        except Exception:
            return signals
        if not bundle:
            return signals

        visibility_available = bool(getattr(bundle, "visibility_available", False)) or signals.visibility_available
        bundle_available = True
        map_available = bool(getattr(bundle, "map_available", False)) or bool(getattr(bundle, "map_file", None)) or signals.map_available
        source_type = signals.source_type
        if source_type == RuntimeSourceType.UNKNOWN:
            source_type = RuntimeSourceType.DONJON_BUNDLE

        return RuntimeModeSignals(
            campaign_id=signals.campaign_id,
            channel_id=signals.channel_id,
            source_type=source_type,
            bundle_available=bundle_available,
            rag_available=signals.rag_available,
            map_available=map_available,
            visibility_available=visibility_available,
            sandbox_enabled=signals.sandbox_enabled,
            avrae_enabled=signals.avrae_enabled,
        )

    @staticmethod
    def _source_type_from_state(state: Dict[str, Any]) -> RuntimeSourceType:
        raw = str(state.get("source_type") or "").strip().upper()
        if not raw:
            return RuntimeSourceType.UNKNOWN
        try:
            return RuntimeSourceType(raw)
        except ValueError:
            aliases = {
                "PDF": RuntimeSourceType.CAMPAIGN_PDF,
                "CAMPAIGN": RuntimeSourceType.RAG_ONLY,
                "RAG": RuntimeSourceType.RAG_ONLY,
                "DONJON": RuntimeSourceType.DONJON_BUNDLE,
                "DUNGEON": RuntimeSourceType.DONJON_BUNDLE,
                "SANDBOX": RuntimeSourceType.SANDBOX,
                "MIXED": RuntimeSourceType.MIXED,
                "HYBRID": RuntimeSourceType.MIXED,
            }
            return aliases.get(raw, RuntimeSourceType.UNKNOWN)
