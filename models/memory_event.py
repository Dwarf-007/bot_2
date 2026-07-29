"""
MODELS/MEMORY_EVENT.PY
Typed models for persistent campaign memory events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MemoryEventRecord:
    id: Optional[int]
    channel_id: str
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
