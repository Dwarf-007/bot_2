from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class SecretDiscoveryState:
    """Campaign/player scoped discovery state.

    `revealed_segments` stores traits revealed for a visibility segment, e.g.:
    {
      "tenebrous:L01:HV0123": ["secret"],
      "tenebrous:L01:HV0456": ["trapped"]
    }
    """

    campaign_id: str
    scope_id: str = "party"
    revealed_segments: Dict[str, List[str]] = field(default_factory=dict)
    discovery_log: List[Dict[str, Any]] = field(default_factory=list)

    def reveal(self, segment_id: str, trait: str, reason: str = "manual", details: Optional[Dict[str, Any]] = None) -> None:
        traits = self.revealed_segments.setdefault(segment_id, [])
        if trait not in traits:
            traits.append(trait)
        self.discovery_log.append({
            "segment_id": segment_id,
            "trait": trait,
            "reason": reason,
            "details": details or {},
        })

    def is_revealed(self, segment_id: str, trait: str) -> bool:
        return trait in self.revealed_segments.get(segment_id, [])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecretDiscoveryState":
        return cls(
            campaign_id=str(data.get("campaign_id") or ""),
            scope_id=str(data.get("scope_id") or "party"),
            revealed_segments={str(k): list(v or []) for k, v in (data.get("revealed_segments") or {}).items()},
            discovery_log=list(data.get("discovery_log") or []),
        )


@dataclass
class DiscoveryCheckResult:
    ok: bool
    message: str
    discovered: List[Dict[str, Any]] = field(default_factory=list)
    candidates_checked: int = 0
    state: Optional[SecretDiscoveryState] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "discovered": self.discovered,
            "candidates_checked": self.candidates_checked,
            "state": self.state.to_dict() if self.state else None,
        }
