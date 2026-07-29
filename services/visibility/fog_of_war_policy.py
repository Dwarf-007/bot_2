"""
SERVICES/VISIBILITY/FOG_OF_WAR_POLICY.PY

Persistent Fog-of-War policy for Sprint 10.3.

This module keeps FOW state updates centralized:
- visible_cells: current visibility after recalculation
- explored_cells: monotonic union of all previously visible cells
- visited_cells: cells physically occupied/traversed by the party
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Optional, Set, Tuple

Cell = Tuple[int, int]


class FogCellState(str, Enum):
    UNKNOWN = "UNKNOWN"
    EXPLORED = "EXPLORED"
    VISIBLE = "VISIBLE"
    CURRENT = "CURRENT"


@dataclass(frozen=True)
class FogOfWarSnapshot:
    visible_cells: Set[Cell]
    explored_cells: Set[Cell]
    visited_cells: Set[Cell]
    current_cell: Optional[Cell] = None

    def cell_state(self, cell: Cell) -> FogCellState:
        normalized = FogOfWarPolicy.normalize_cell(cell)
        if normalized is None:
            return FogCellState.UNKNOWN
        if self.current_cell is not None and normalized == self.current_cell:
            return FogCellState.CURRENT
        if normalized in self.visible_cells:
            return FogCellState.VISIBLE
        if normalized in self.explored_cells:
            return FogCellState.EXPLORED
        return FogCellState.UNKNOWN

    def to_counts(self) -> Dict[str, int]:
        return {
            "visible_cells": len(self.visible_cells),
            "explored_cells": len(self.explored_cells),
            "visited_cells": len(self.visited_cells),
            "has_current_cell": 1 if self.current_cell is not None else 0,
        }


class FogOfWarPolicy:
    """Central policy for updating and reading persistent FOW state."""

    @staticmethod
    def normalize_cell(value: Any) -> Optional[Cell]:
        if value is None:
            return None
        try:
            r, c = value
            return int(r), int(c)
        except Exception:
            return None

    @classmethod
    def normalize_cells(cls, values: Iterable[Any] | None) -> Set[Cell]:
        out: Set[Cell] = set()
        for item in values or []:
            cell = cls.normalize_cell(item)
            if cell is not None:
                out.add(cell)
        return out

    @classmethod
    def current_cell(cls, state: Any) -> Optional[Cell]:
        current = getattr(state, "current", None)
        raw = getattr(current, "cell", None) if current else None
        return cls.normalize_cell(raw)

    @classmethod
    def apply_visible_cells(cls, state: Any, visible_cells: Iterable[Any]) -> Any:
        """Update current visibility and persistently merge it into explored_cells."""
        normalized_visible = cls.normalize_cells(visible_cells)
        previous_explored = cls.normalize_cells(getattr(state, "explored_cells", []) or [])
        merged_explored = previous_explored | normalized_visible

        state.visible_cells = sorted(normalized_visible)
        state.explored_cells = sorted(merged_explored)
        return state

    @classmethod
    def mark_current_cell_visited(cls, state: Any) -> Any:
        """Add current.cell to visited_cells when the current position has a cell anchor."""
        cell = cls.current_cell(state)
        if cell is None:
            return state
        visited = cls.normalize_cells(getattr(state, "visited_cells", []) or [])
        visited.add(cell)
        state.visited_cells = sorted(visited)
        return state

    @classmethod
    def apply_after_visibility_refresh(cls, state: Any, visible_cells: Iterable[Any]) -> Any:
        """Recommended one-call update after every look/move visibility recalculation."""
        cls.apply_visible_cells(state, visible_cells)
        cls.mark_current_cell_visited(state)
        return state

    @classmethod
    def snapshot(cls, state: Any) -> FogOfWarSnapshot:
        return FogOfWarSnapshot(
            visible_cells=cls.normalize_cells(getattr(state, "visible_cells", []) or []),
            explored_cells=cls.normalize_cells(getattr(state, "explored_cells", []) or []),
            visited_cells=cls.normalize_cells(getattr(state, "visited_cells", []) or []),
            current_cell=cls.current_cell(state),
        )
