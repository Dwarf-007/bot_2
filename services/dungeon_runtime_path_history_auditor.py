
"""
SERVICES/DUNGEON_RUNTIME_PATH_HISTORY_AUDITOR.PY

Sprint 13.0 / 13.1-prep - Path History Audit.

Purpose:
- Audit existing Dungeon Runtime visibility state's path_history without mutating it.
- Detect structural problems, repeated adjacent entries, current==last-history issues,
  and short ping-pong loops that can cause history bloat.
- Provide machine-readable recommendations before Room Discovery Engine work.

This module is intentionally read-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

Cell = Tuple[int, int]
PositionKey = Tuple[str, str, int, Optional[str], Optional[str], Optional[Cell]]


@dataclass(frozen=True)
class PathHistoryAuditCheck:
    name: str
    status: str  # OK | WARN | FAIL
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {"OK", "WARN"}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PathHistoryAuditResult:
    ok: bool
    status: str  # OK | WARN | FAIL
    state_file: str = ""
    campaign_id: str = ""
    current_key: Optional[PositionKey] = None
    current_node_id: Optional[str] = None
    current_node_type: str = ""
    path_history_count: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    unique_positions: int = 0
    adjacent_duplicate_count: int = 0
    current_equals_last_history: bool = False
    ping_pong_pair_count: int = 0
    longest_repeated_tail_count: int = 0
    recommendations: List[str] = field(default_factory=list)
    checks: List[PathHistoryAuditCheck] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "state_file": self.state_file,
            "campaign_id": self.campaign_id,
            "current_key": self._position_key_to_dict(self.current_key),
            "current_node_id": self.current_node_id,
            "current_node_type": self.current_node_type,
            "path_history_count": self.path_history_count,
            "valid_entries": self.valid_entries,
            "invalid_entries": self.invalid_entries,
            "unique_positions": self.unique_positions,
            "adjacent_duplicate_count": self.adjacent_duplicate_count,
            "current_equals_last_history": self.current_equals_last_history,
            "ping_pong_pair_count": self.ping_pong_pair_count,
            "longest_repeated_tail_count": self.longest_repeated_tail_count,
            "recommendations": list(self.recommendations),
            "checks": [check.to_dict() for check in self.checks],
        }

    def summary_text(self) -> str:
        lines = [
            f"Dungeon Runtime Path History Audit: {self.status}",
            f"campaign_id={self.campaign_id}",
            f"state_file={self.state_file}",
            f"current_node_id={self.current_node_id}",
            f"current_node_type={self.current_node_type}",
            f"path_history_count={self.path_history_count}",
            f"valid_entries={self.valid_entries}",
            f"invalid_entries={self.invalid_entries}",
            f"unique_positions={self.unique_positions}",
            f"adjacent_duplicate_count={self.adjacent_duplicate_count}",
            f"current_equals_last_history={self.current_equals_last_history}",
            f"ping_pong_pair_count={self.ping_pong_pair_count}",
            f"longest_repeated_tail_count={self.longest_repeated_tail_count}",
        ]
        if self.recommendations:
            lines.append("Recommendations:")
            for item in self.recommendations:
                lines.append(f"- {item}")
        lines.append("Checks:")
        for check in self.checks:
            lines.append(f"- {check.status} {check.name}: {check.message}")
        return "\n".join(lines)

    @staticmethod
    def _position_key_to_dict(key: Optional[PositionKey]) -> Optional[Dict[str, Any]]:
        if key is None:
            return None
        node_id, node_type, level, room_id, segment_id, cell = key
        return {
            "node_id": node_id,
            "node_type": node_type,
            "level": level,
            "room_id": room_id,
            "segment_id": segment_id,
            "cell": list(cell) if cell else None,
        }


class DungeonRuntimePathHistoryAuditor:
    """Read-only path_history auditor for VisibilityState JSON dictionaries."""

    def audit_file(self, state_file: str | Path) -> PathHistoryAuditResult:
        path = Path(state_file)
        if not path.exists():
            check = PathHistoryAuditCheck("state_file_exists", "FAIL", f"State file does not exist: {path}")
            return PathHistoryAuditResult(False, "FAIL", state_file=str(path), checks=[check], recommendations=["Run a green-path smoke first, or check the channel-specific state file path."])
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            check = PathHistoryAuditCheck("state_file_json", "FAIL", f"State file is not valid JSON: {exc}")
            return PathHistoryAuditResult(False, "FAIL", state_file=str(path), checks=[check], recommendations=["Inspect the state file; it must be valid UTF-8 JSON."])
        return self.audit_state_dict(data, state_file=str(path))

    def audit_state_dict(self, data: Dict[str, Any], *, state_file: str = "") -> PathHistoryAuditResult:
        checks: List[PathHistoryAuditCheck] = []
        recommendations: List[str] = []
        campaign_id = str(data.get("campaign_id") or "")
        current_raw = data.get("current") or {}
        current_key = self.position_key(current_raw)
        current_node_id = current_key[0] if current_key else None
        current_node_type = current_key[1] if current_key else ""
        raw_history = data.get("path_history")

        if not campaign_id:
            checks.append(PathHistoryAuditCheck("campaign_id_present", "FAIL", "campaign_id is missing."))
        else:
            checks.append(PathHistoryAuditCheck("campaign_id_present", "OK", "campaign_id is present."))

        if current_key is None:
            checks.append(PathHistoryAuditCheck("current_position_valid", "FAIL", "current position is missing or invalid."))
        else:
            checks.append(PathHistoryAuditCheck("current_position_valid", "OK", "current position is valid."))

        if not isinstance(raw_history, list):
            checks.append(PathHistoryAuditCheck("path_history_list", "FAIL", "path_history is not a list."))
            return self._build_result(
                checks=checks,
                recommendations=recommendations + ["Ensure visibility runtime state always serializes path_history as a list."],
                campaign_id=campaign_id,
                state_file=state_file,
                current_key=current_key,
                current_node_id=current_node_id,
                current_node_type=current_node_type,
            )

        checks.append(PathHistoryAuditCheck("path_history_list", "OK", "path_history is a list.", {"count": len(raw_history)}))
        parsed: List[PositionKey] = []
        invalid_entries: List[Dict[str, Any]] = []
        for idx, entry in enumerate(raw_history):
            key = self.position_key(entry)
            if key is None:
                invalid_entries.append({"index": idx, "entry_type": type(entry).__name__})
            else:
                parsed.append(key)

        if invalid_entries:
            checks.append(PathHistoryAuditCheck(
                "path_history_entries_valid",
                "FAIL",
                f"{len(invalid_entries)} path_history entries are invalid.",
                {"invalid_sample": invalid_entries[:10]},
            ))
            recommendations.append("Normalize path_history entries to VisibilityPosition-like dictionaries before relying on backtracking semantics.")
        else:
            checks.append(PathHistoryAuditCheck("path_history_entries_valid", "OK", "All path_history entries are position-like."))

        adjacent_duplicates = self.count_adjacent_duplicates(parsed)
        if adjacent_duplicates:
            checks.append(PathHistoryAuditCheck(
                "adjacent_duplicates",
                "WARN",
                f"Found {adjacent_duplicates} adjacent duplicate path entries.",
                {"count": adjacent_duplicates},
            ))
            recommendations.append("Avoid appending a history entry when the previous history entry is the same position.")
        else:
            checks.append(PathHistoryAuditCheck("adjacent_duplicates", "OK", "No adjacent duplicate entries found."))

        current_equals_last = bool(parsed and current_key is not None and parsed[-1] == current_key)
        if current_equals_last:
            checks.append(PathHistoryAuditCheck(
                "current_not_last_history",
                "WARN",
                "Current position equals the last path_history entry.",
            ))
            recommendations.append("Do not append the destination/current position to path_history; keep only previous positions for backtracking.")
        else:
            checks.append(PathHistoryAuditCheck("current_not_last_history", "OK", "Current position is not duplicated as the last history entry."))

        ping_pong_count = self.count_ping_pong_pairs(parsed)
        if ping_pong_count:
            checks.append(PathHistoryAuditCheck(
                "ping_pong_pattern",
                "WARN",
                f"Detected {ping_pong_count} A/B/A/B short-loop pattern(s).",
                {"count": ping_pong_count, "sample": [self.key_to_dict(x) for x in parsed[:8]]},
            ))
            recommendations.append("Audit move/back history mutation: repeated A/B/A/B often means both forward move and back/look persistence append previous/current positions multiple times.")
        else:
            checks.append(PathHistoryAuditCheck("ping_pong_pattern", "OK", "No short ping-pong history pattern detected."))

        unique_positions = len(set(parsed))
        if len(parsed) >= 8 and unique_positions <= max(2, len(parsed) // 4):
            checks.append(PathHistoryAuditCheck(
                "history_density",
                "WARN",
                f"History has {len(parsed)} entries but only {unique_positions} unique positions.",
                {"path_history_count": len(parsed), "unique_positions": unique_positions},
            ))
            recommendations.append("Consider compacting internal segment history or storing an audit trail separately from backtracking stack.")
        else:
            checks.append(PathHistoryAuditCheck("history_density", "OK", "History density looks acceptable.", {"path_history_count": len(parsed), "unique_positions": unique_positions}))

        longest_tail = self.longest_repeated_tail_count(parsed)
        if longest_tail >= 4:
            checks.append(PathHistoryAuditCheck(
                "repeated_tail",
                "WARN",
                f"The tail of path_history repeats for {longest_tail} entries.",
                {"longest_repeated_tail_count": longest_tail},
            ))
            recommendations.append("Investigate whether repeated smoke commands append the same room/segment pair repeatedly after backtracking.")
        else:
            checks.append(PathHistoryAuditCheck("repeated_tail", "OK", "No excessive repeated tail detected.", {"longest_repeated_tail_count": longest_tail}))

        return self._build_result(
            checks=checks,
            recommendations=recommendations,
            campaign_id=campaign_id,
            state_file=state_file,
            current_key=current_key,
            current_node_id=current_node_id,
            current_node_type=current_node_type,
            path_history_count=len(raw_history),
            valid_entries=len(parsed),
            invalid_entries=len(invalid_entries),
            unique_positions=unique_positions,
            adjacent_duplicate_count=adjacent_duplicates,
            current_equals_last_history=current_equals_last,
            ping_pong_pair_count=ping_pong_count,
            longest_repeated_tail_count=longest_tail,
        )

    def _build_result(
        self,
        *,
        checks: List[PathHistoryAuditCheck],
        recommendations: List[str],
        campaign_id: str = "",
        state_file: str = "",
        current_key: Optional[PositionKey] = None,
        current_node_id: Optional[str] = None,
        current_node_type: str = "",
        path_history_count: int = 0,
        valid_entries: int = 0,
        invalid_entries: int = 0,
        unique_positions: int = 0,
        adjacent_duplicate_count: int = 0,
        current_equals_last_history: bool = False,
        ping_pong_pair_count: int = 0,
        longest_repeated_tail_count: int = 0,
    ) -> PathHistoryAuditResult:
        has_fail = any(check.status == "FAIL" for check in checks)
        has_warn = any(check.status == "WARN" for check in checks)
        status = "FAIL" if has_fail else "WARN" if has_warn else "OK"
        return PathHistoryAuditResult(
            ok=not has_fail,
            status=status,
            state_file=state_file,
            campaign_id=campaign_id,
            current_key=current_key,
            current_node_id=current_node_id,
            current_node_type=current_node_type,
            path_history_count=path_history_count,
            valid_entries=valid_entries,
            invalid_entries=invalid_entries,
            unique_positions=unique_positions,
            adjacent_duplicate_count=adjacent_duplicate_count,
            current_equals_last_history=current_equals_last_history,
            ping_pong_pair_count=ping_pong_pair_count,
            longest_repeated_tail_count=longest_repeated_tail_count,
            recommendations=self._dedupe(recommendations),
            checks=checks,
        )

    @classmethod
    def position_key(cls, value: Any) -> Optional[PositionKey]:
        if hasattr(value, "to_dict"):
            value = value.to_dict()
        if not isinstance(value, dict):
            return None
        node_id = str(value.get("node_id") or value.get("room_id") or value.get("segment_id") or "")
        node_type = str(value.get("node_type") or ("room" if value.get("room_id") else "segment" if value.get("segment_id") else ""))
        if not node_id or not node_type:
            return None
        try:
            level = int(value.get("level") or 1)
        except Exception:
            level = 1
        room_id = value.get("room_id")
        segment_id = value.get("segment_id")
        cell = cls.cell_from_any(value.get("cell"))
        return (node_id, node_type, level, str(room_id) if room_id else None, str(segment_id) if segment_id else None, cell)

    @staticmethod
    def cell_from_any(value: Any) -> Optional[Cell]:
        if value is None:
            return None
        try:
            r, c = value
            return int(r), int(c)
        except Exception:
            return None

    @staticmethod
    def key_to_dict(key: PositionKey) -> Dict[str, Any]:
        node_id, node_type, level, room_id, segment_id, cell = key
        return {
            "node_id": node_id,
            "node_type": node_type,
            "level": level,
            "room_id": room_id,
            "segment_id": segment_id,
            "cell": list(cell) if cell else None,
        }

    @staticmethod
    def count_adjacent_duplicates(keys: List[PositionKey]) -> int:
        return sum(1 for a, b in zip(keys, keys[1:]) if a == b)

    @staticmethod
    def count_ping_pong_pairs(keys: List[PositionKey]) -> int:
        if len(keys) < 4:
            return 0
        count = 0
        for i in range(len(keys) - 3):
            a, b, c, d = keys[i], keys[i + 1], keys[i + 2], keys[i + 3]
            if a == c and b == d and a != b:
                count += 1
        return count

    @staticmethod
    def longest_repeated_tail_count(keys: List[PositionKey]) -> int:
        if not keys:
            return 0
        tail = keys[-1]
        count = 0
        for item in reversed(keys):
            if item == tail:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _dedupe(values: Iterable[str]) -> List[str]:
        out: List[str] = []
        for value in values:
            if value and value not in out:
                out.append(value)
        return out
