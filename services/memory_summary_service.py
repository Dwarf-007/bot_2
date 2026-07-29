"""
SERVICES/MEMORY_SUMMARY_SERVICE.PY
Lightweight deterministic summary rendering for recent memory events.

This is intentionally not an LLM summarizer yet. It produces compact text that
can be injected into prompts as long-term memory context.
"""

from __future__ import annotations

from typing import Iterable, List

from models.memory_event import MemoryEventRecord


class MemorySummaryService:
    def build_recent_summary(self, events: Iterable[MemoryEventRecord], max_lines: int = 12) -> str:
        lines: List[str] = []
        for event in list(events)[-max_lines:]:
            lines.append(self._format_event(event))
        return "\n".join(line for line in lines if line)

    def _format_event(self, event: MemoryEventRecord) -> str:
        data = event.data or {}
        event_type = event.event_type

        if event_type == "player_moved":
            return f"- Mozgás: {data.get('from_room')} → {data.get('to_room')} ({data.get('direction', 'ismeretlen irány')})."
        if event_type == "trap_triggered":
            return f"- Csapda aktiválódott: {data.get('trap_name')} a(z) {data.get('room_id')} helyszínen."
        if event_type == "combat_start":
            return f"- Harc kezdődött: {data.get('room_id', data.get('channel_id', 'ismeretlen hely'))}."
        if event_type in {"combat_end", "all_monsters_defeated"}:
            return "- Egy harc véget ért."
        if event_type == "rest_completed":
            return f"- Pihenő sikeres: {data.get('rest_type', 'UNKNOWN')}."
        if event_type == "rest_interrupted":
            return f"- Pihenő megszakadt: {data.get('reason', 'ismeretlen ok')}."
        if event_type == "inventory_updated":
            return f"- Felszerelés változott: játékos {data.get('player_id', 'ismeretlen')}."
        if event_type == "xp_gained":
            return f"- XP kiosztás: {data.get('xp_each', '?')}/fő."
        if event_type == "required_check":
            return f"- Dobáskérés: {data.get('check')} DC {data.get('dc')}."
        return f"- {event_type}: {data}"
