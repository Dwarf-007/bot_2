
"""
MODELS/CAMPAIGN.PY
Typed DTOs for campaign registry and active campaign state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CampaignRecord:
    campaign_id: str
    name: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    party_size: Optional[int] = None
    party_level: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class CampaignStatus:
    campaign_id: str
    name: str
    active_channel_id: Optional[str]
    room_count: int = 0
    rag_chunk_count: int = 0
    memory_event_count: int = 0
