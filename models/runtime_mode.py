"""
MODELS/RUNTIME_MODE.PY
Runtime mode detection models for the AI DM platform.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional

class RuntimeMode(str, Enum):
    UNKNOWN = "UNKNOWN"
    CAMPAIGN = "CAMPAIGN"
    DUNGEON = "DUNGEON"
    SANDBOX = "SANDBOX"
    HYBRID = "HYBRID"

class RuntimeSourceType(str, Enum):
    UNKNOWN = "UNKNOWN"
    CAMPAIGN_PDF = "CAMPAIGN_PDF"
    FANMADE_PDF = "FANMADE_PDF"
    RAG_ONLY = "RAG_ONLY"
    DONJON_BUNDLE = "DONJON_BUNDLE"
    GENERATED_DUNGEON = "GENERATED_DUNGEON"
    SANDBOX = "SANDBOX"
    MIXED = "MIXED"

@dataclass(frozen=True)
class RuntimeModeSignals:
    campaign_id: str = ""
    channel_id: str = ""
    source_type: RuntimeSourceType = RuntimeSourceType.UNKNOWN
    bundle_available: bool = False
    rag_available: bool = False
    map_available: bool = False
    visibility_available: bool = False
    sandbox_enabled: bool = False
    avrae_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "RuntimeModeSignals":
        data = data or {}
        raw_source = str(data.get("source_type") or RuntimeSourceType.UNKNOWN.value)
        try:
            source_type = RuntimeSourceType(raw_source)
        except ValueError:
            source_type = RuntimeSourceType.UNKNOWN
        return cls(
            campaign_id=str(data.get("campaign_id") or ""),
            channel_id=str(data.get("channel_id") or ""),
            source_type=source_type,
            bundle_available=bool(data.get("bundle_available", False)),
            rag_available=bool(data.get("rag_available", False)),
            map_available=bool(data.get("map_available", False)),
            visibility_available=bool(data.get("visibility_available", False)),
            sandbox_enabled=bool(data.get("sandbox_enabled", False)),
            avrae_enabled=bool(data.get("avrae_enabled", False)),
        )

@dataclass(frozen=True)
class RuntimeModeDecision:
    mode: RuntimeMode
    signals: RuntimeModeSignals
    reason: str = ""
    dungeon_runtime_enabled: bool = False
    campaign_runtime_enabled: bool = False
    sandbox_runtime_enabled: bool = False
    avrae_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "reason": self.reason,
            "signals": self.signals.to_dict(),
            "dungeon_runtime_enabled": self.dungeon_runtime_enabled,
            "campaign_runtime_enabled": self.campaign_runtime_enabled,
            "sandbox_runtime_enabled": self.sandbox_runtime_enabled,
            "avrae_enabled": self.avrae_enabled,
        }
