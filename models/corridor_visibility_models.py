"""
MODELS/CORRIDOR_VISIBILITY_MODELS.PY

Sprint 10.3 update:
- Adds persistent cell-level Fog-of-War fields:
  - explored_cells: cells the party has ever seen
  - visited_cells: cells the party has physically occupied/traversed
- Keeps backward compatibility with existing JSON state files.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

Cell = Tuple[int, int]


def _cell_from_any(value: Any) -> Optional[Cell]:
    """Best-effort conversion of a JSON/list/tuple cell into a normalized cell tuple."""
    if value is None:
        return None
    try:
        r, c = value
        return int(r), int(c)
    except Exception:
        return None


def _cells_from_any(values: Any) -> List[Cell]:
    """Normalize a JSON cell list while ignoring malformed entries."""
    out: List[Cell] = []
    seen = set()
    for item in values or []:
        cell = _cell_from_any(item)
        if cell is None or cell in seen:
            continue
        seen.add(cell)
        out.append(cell)
    return out


def _cells_to_json(cells: List[Cell]) -> List[List[int]]:
    return [[int(r), int(c)] for r, c in (cells or [])]


@dataclass
class VisibilitySegment:
    segment_id: str
    level: int
    segment_type: str  # corridor_segment | junction | doorway | stair | dead_end
    cells: List[Cell] = field(default_factory=list)
    endpoints: List[Cell] = field(default_factory=list)
    connected_segments: List[str] = field(default_factory=list)
    adjacent_rooms: List[str] = field(default_factory=list)
    direction_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['cells'] = _cells_to_json(self.cells)
        data['endpoints'] = _cells_to_json(self.endpoints)
        return data


@dataclass
class VisibilityPosition:
    node_id: str
    node_type: str  # room | segment
    level: int
    room_id: Optional[str] = None
    segment_id: Optional[str] = None
    cell: Optional[Cell] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.cell is not None:
            data['cell'] = [int(self.cell[0]), int(self.cell[1])]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisibilityPosition':
        data = data or {}
        return cls(
            node_id=str(data.get('node_id') or data.get('room_id') or data.get('segment_id') or ''),
            node_type=str(data.get('node_type') or ('room' if data.get('room_id') else 'segment')),
            level=int(data.get('level') or 1),
            room_id=data.get('room_id'),
            segment_id=data.get('segment_id'),
            cell=_cell_from_any(data.get('cell')),
        )


@dataclass
class VisibilityState:
    campaign_id: str
    current: VisibilityPosition
    visited_rooms: List[str] = field(default_factory=list)
    visited_segments: List[str] = field(default_factory=list)
    visible_cells: List[Cell] = field(default_factory=list)
    explored_cells: List[Cell] = field(default_factory=list)
    visited_cells: List[Cell] = field(default_factory=list)
    path_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['current'] = self.current.to_dict()
        data['visible_cells'] = _cells_to_json(self.visible_cells)
        data['explored_cells'] = _cells_to_json(self.explored_cells)
        data['visited_cells'] = _cells_to_json(self.visited_cells)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisibilityState':
        data = data or {}
        pos = VisibilityPosition.from_dict(data.get('current') or {})
        visible_cells = _cells_from_any(data.get('visible_cells') or [])

        # Backward-compatible migration:
        # old state files do not contain explored_cells / visited_cells.
        explored_cells = _cells_from_any(data.get('explored_cells') or [])
        if not explored_cells:
            explored_cells = list(visible_cells)

        visited_cells = _cells_from_any(data.get('visited_cells') or [])
        if not visited_cells and pos.cell is not None:
            visited_cells = [pos.cell]

        return cls(
            campaign_id=str(data.get('campaign_id') or ''),
            current=pos,
            visited_rooms=list(data.get('visited_rooms') or []),
            visited_segments=list(data.get('visited_segments') or []),
            visible_cells=visible_cells,
            explored_cells=explored_cells,
            visited_cells=visited_cells,
            path_history=list(data.get('path_history') or []),
        )

    def record_visible_cells(self, cells: List[Cell]) -> None:
        """Set current visible cells and merge them into persistent explored_cells."""
        normalized = _cells_from_any(cells)
        self.visible_cells = sorted(normalized)
        explored = set(_cells_from_any(self.explored_cells))
        explored.update(normalized)
        self.explored_cells = sorted(explored)

    def mark_current_cell_visited(self) -> None:
        """Record current.cell, when available, as physically visited."""
        cell = _cell_from_any(getattr(self.current, 'cell', None))
        if cell is None:
            return
        visited = set(_cells_from_any(self.visited_cells))
        visited.add(cell)
        self.visited_cells = sorted(visited)
