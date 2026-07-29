"""
SERVICES/RUNTIME_MODE_SERVICE.PY
Runtime mode detection service for Sprint 10.2.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
from models.runtime_mode import RuntimeMode, RuntimeModeDecision, RuntimeModeSignals, RuntimeSourceType

class RuntimeModeService:
    def __init__(self, project_root: str | Path = ".", campaign_repo: Any = None) -> None:
        self.project_root = Path(project_root)
        self.campaign_repo = campaign_repo

    def decide(self, signals: RuntimeModeSignals) -> RuntimeModeDecision:
        dungeon_ready = bool(signals.bundle_available and (signals.visibility_available or signals.map_available))
        campaign_ready = bool(signals.rag_available or signals.source_type in {RuntimeSourceType.CAMPAIGN_PDF, RuntimeSourceType.FANMADE_PDF, RuntimeSourceType.RAG_ONLY})
        sandbox_ready = bool(signals.sandbox_enabled or signals.source_type == RuntimeSourceType.SANDBOX)
        enabled_count = sum([dungeon_ready, campaign_ready, sandbox_ready])
        if enabled_count >= 2:
            return RuntimeModeDecision(RuntimeMode.HYBRID, signals, "Multiple runtime capabilities are available.", dungeon_ready, campaign_ready, sandbox_ready, signals.avrae_enabled)
        if dungeon_ready:
            return RuntimeModeDecision(RuntimeMode.DUNGEON, signals, "Structured dungeon bundle/map/visibility capability is available.", True, False, False, signals.avrae_enabled)
        if campaign_ready:
            return RuntimeModeDecision(RuntimeMode.CAMPAIGN, signals, "Campaign/RAG source capability is available without dungeon runtime.", False, True, False, signals.avrae_enabled)
        if sandbox_ready:
            return RuntimeModeDecision(RuntimeMode.SANDBOX, signals, "Sandbox mode is enabled without fixed campaign/dungeon source.", False, False, True, signals.avrae_enabled)
        return RuntimeModeDecision(RuntimeMode.UNKNOWN, signals, "No runtime capability signals were detected.", False, False, False, signals.avrae_enabled)

    def decide_from_dict(self, data: Optional[Dict[str, Any]]) -> RuntimeModeDecision:
        return self.decide(RuntimeModeSignals.from_dict(data))

    def inspect_bundle_dir(self, bundle_dir: str | Path) -> Dict[str, bool]:
        root = Path(bundle_dir)
        if not root.exists() or not root.is_dir():
            return {"bundle_available": False, "map_available": False, "visibility_available": False}
        visibility_files = [root / "corridor_visibility_graph.json", root / "visibility_state.json", root / "secret_discovery_state.json"]
        visibility_available = any(p.exists() for p in visibility_files) or any(root.rglob("*.tsv"))
        map_available = any(("map" in p.name.lower() or "player" in p.name.lower()) for p in root.rglob("*.png"))
        return {"bundle_available": True, "map_available": map_available, "visibility_available": visibility_available}

    def decide_for_bundle(self, *, campaign_id: str, channel_id: str, bundle_dir: str | Path, rag_available: bool = False, sandbox_enabled: bool = False, avrae_enabled: bool = False) -> RuntimeModeDecision:
        inspected = self.inspect_bundle_dir(bundle_dir)
        signals = RuntimeModeSignals(
            campaign_id=campaign_id,
            channel_id=channel_id,
            source_type=RuntimeSourceType.DONJON_BUNDLE if inspected["bundle_available"] else RuntimeSourceType.UNKNOWN,
            bundle_available=inspected["bundle_available"],
            rag_available=rag_available,
            map_available=inspected["map_available"],
            visibility_available=inspected["visibility_available"],
            sandbox_enabled=sandbox_enabled,
            avrae_enabled=avrae_enabled,
        )
        return self.decide(signals)
