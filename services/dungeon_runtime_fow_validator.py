
"""
SERVICES/DUNGEON_RUNTIME_FOW_VALIDATOR.PY

Sprint 12.6 - Persistent FOW Validation.

Purpose:
- Validate actual Dungeon Runtime visibility state after green-path smoke.
- Ensure local/full map hardening did not hide semantic FOW issues.
- Check that visible/explored/current/path-history data is structurally usable.

This validator is intentionally read-only. It does not mutate runtime state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

Cell = Tuple[int, int]


@dataclass(frozen=True)
class DungeonRuntimeFowCheck:
    name: str
    ok: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DungeonRuntimeFowValidationResult:
    ok: bool
    campaign_id: str
    channel_id: str
    state_file: str
    checks: list[DungeonRuntimeFowCheck] = field(default_factory=list)
    visible_cells_count: int = 0
    explored_cells_count: int = 0
    visited_cells_count: int = 0
    path_history_count: int = 0
    current_cell: Optional[Cell] = None
    current_node_type: str = ""
    current_room_id: Optional[str] = None
    current_segment_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "campaign_id": self.campaign_id,
            "channel_id": self.channel_id,
            "state_file": self.state_file,
            "visible_cells_count": self.visible_cells_count,
            "explored_cells_count": self.explored_cells_count,
            "visited_cells_count": self.visited_cells_count,
            "path_history_count": self.path_history_count,
            "current_cell": list(self.current_cell) if self.current_cell else None,
            "current_node_type": self.current_node_type,
            "current_room_id": self.current_room_id,
            "current_segment_id": self.current_segment_id,
            "checks": [check.to_dict() for check in self.checks],
        }

    def summary_text(self) -> str:
        lines = [
            f"Dungeon Runtime FOW validation: {'OK' if self.ok else 'FAIL'}",
            f"campaign_id={self.campaign_id}",
            f"channel_id={self.channel_id}",
            f"state_file={self.state_file}",
            f"visible_cells_count={self.visible_cells_count}",
            f"explored_cells_count={self.explored_cells_count}",
            f"visited_cells_count={self.visited_cells_count}",
            f"path_history_count={self.path_history_count}",
            f"current_node_type={self.current_node_type}",
            f"current_room_id={self.current_room_id}",
            f"current_segment_id={self.current_segment_id}",
        ]
        lines.append("Checks:")
        for check in self.checks:
            lines.append(f"- {'OK' if check.ok else 'FAIL'} {check.name}: {check.message}")
        return "\n".join(lines)


class DungeonRuntimeFowValidator:
    """Validates channel-scoped visibility runtime state."""

    def validate_state_file(
        self,
        *,
        state_file: str | Path,
        campaign_id: str = "",
        channel_id: str = "",
        require_visible_cells: bool = True,
        require_explored_superset: bool = True,
        require_current_cell_when_segment: bool = False,
    ) -> DungeonRuntimeFowValidationResult:
        path = Path(state_file)
        if not path.exists():
            check = DungeonRuntimeFowCheck("state_file_exists", False, f"State file does not exist: {path}")
            return DungeonRuntimeFowValidationResult(False, campaign_id, channel_id, str(path), checks=[check])

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            check = DungeonRuntimeFowCheck("state_file_json", False, f"State file is not valid JSON: {exc}")
            return DungeonRuntimeFowValidationResult(False, campaign_id, channel_id, str(path), checks=[check])

        return self.validate_state_dict(
            data,
            campaign_id=campaign_id or str(data.get("campaign_id") or ""),
            channel_id=channel_id,
            state_file=str(path),
            require_visible_cells=require_visible_cells,
            require_explored_superset=require_explored_superset,
            require_current_cell_when_segment=require_current_cell_when_segment,
        )

    def validate_state_dict(
        self,
        data: Dict[str, Any],
        *,
        campaign_id: str = "",
        channel_id: str = "",
        state_file: str = "",
        require_visible_cells: bool = True,
        require_explored_superset: bool = True,
        require_current_cell_when_segment: bool = False,
    ) -> DungeonRuntimeFowValidationResult:
        checks: list[DungeonRuntimeFowCheck] = []
        current = data.get("current") or {}
        visible = self._cell_set(data.get("visible_cells") or [])
        explored = self._cell_set(data.get("explored_cells") or [])
        visited = self._cell_set(data.get("visited_cells") or [])
        current_cell = self._cell_from_any(current.get("cell"))
        current_node_type = str(current.get("node_type") or "")
        current_room_id = current.get("room_id")
        current_segment_id = current.get("segment_id")
        path_history = data.get("path_history") or []

        checks.append(DungeonRuntimeFowCheck(
            "campaign_id_present",
            bool(data.get("campaign_id") or campaign_id),
            "campaign_id is present." if bool(data.get("campaign_id") or campaign_id) else "campaign_id is missing.",
        ))
        checks.append(DungeonRuntimeFowCheck(
            "current_present",
            isinstance(current, dict) and bool(current),
            "current position exists." if isinstance(current, dict) and bool(current) else "current position is missing.",
        ))
        checks.append(DungeonRuntimeFowCheck(
            "visible_cells_non_empty",
            (len(visible) > 0) if require_visible_cells else True,
            f"visible_cells count={len(visible)}" if len(visible) > 0 else "visible_cells is empty.",
            {"count": len(visible), "required": require_visible_cells},
        ))
        checks.append(DungeonRuntimeFowCheck(
            "explored_cells_non_empty",
            len(explored) > 0,
            f"explored_cells count={len(explored)}" if explored else "explored_cells is empty.",
            {"count": len(explored)},
        ))
        missing_from_explored = sorted(visible - explored)
        checks.append(DungeonRuntimeFowCheck(
            "explored_contains_visible",
            (not missing_from_explored) if require_explored_superset else True,
            "explored_cells contains all currently visible cells." if not missing_from_explored else f"explored_cells misses {len(missing_from_explored)} visible cells.",
            {"missing_count": len(missing_from_explored), "missing_sample": [list(x) for x in missing_from_explored[:10]]},
        ))
        checks.append(DungeonRuntimeFowCheck(
            "visited_cells_structural",
            isinstance(data.get("visited_cells", []), list),
            f"visited_cells count={len(visited)}",
            {"count": len(visited)},
        ))
        checks.append(DungeonRuntimeFowCheck(
            "path_history_structural",
            isinstance(path_history, list),
            f"path_history count={len(path_history)}" if isinstance(path_history, list) else "path_history is not a list.",
            {"count": len(path_history) if isinstance(path_history, list) else None},
        ))
        if require_current_cell_when_segment and current_node_type == "segment":
            checks.append(DungeonRuntimeFowCheck(
                "segment_current_cell_present",
                current_cell is not None,
                "current segment has a current.cell." if current_cell else "current segment has no current.cell.",
            ))

        ok = all(check.ok for check in checks)
        return DungeonRuntimeFowValidationResult(
            ok=ok,
            campaign_id=campaign_id or str(data.get("campaign_id") or ""),
            channel_id=channel_id,
            state_file=state_file,
            checks=checks,
            visible_cells_count=len(visible),
            explored_cells_count=len(explored),
            visited_cells_count=len(visited),
            path_history_count=len(path_history) if isinstance(path_history, list) else 0,
            current_cell=current_cell,
            current_node_type=current_node_type,
            current_room_id=current_room_id,
            current_segment_id=current_segment_id,
        )

    @staticmethod
    def _cell_from_any(value: Any) -> Optional[Cell]:
        if value is None:
            return None
        try:
            r, c = value
            return int(r), int(c)
        except Exception:
            return None

    @classmethod
    def _cell_set(cls, values: Iterable[Any]) -> Set[Cell]:
        out: Set[Cell] = set()
        for value in values or []:
            cell = cls._cell_from_any(value)
            if cell is not None:
                out.add(cell)
        return out
