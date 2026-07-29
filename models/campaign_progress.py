
"""
MODELS/CAMPAIGN_PROGRESS.PY
DTOs for campaign progress, scenes, and objectives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CampaignSceneRecord:
    campaign_id: str
    scene_id: str
    title: str
    order_index: int = 0
    room_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChannelProgressRecord:
    channel_id: str
    campaign_id: str
    current_scene_id: Optional[str] = None
    current_room_id: Optional[str] = None
    milestone: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CampaignObjectiveRecord:
    objective_id: int
    channel_id: str
    campaign_id: str
    text: str
    status: str = "OPEN"
    scene_id: Optional[str] = None
    room_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
