"""
SERVICES/COMBAT_EVENT_HANDLER.PY
Converts COMBAT_START domain events into advisory command recommendations.

C3.5 boundary rule:
- This handler does not dispatch Avrae commands.
- Returned command dictionaries use type="suggested_command".
- Callers may render these commands to the DM as copy/paste suggestions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.game_events import EventTypes, GameEvent


class CombatEventHandler:
    """
    Handles EventTypes.COMBAT_START.

    Basic behavior:
        - Always recommends !init begin.
        - If payload contains monsters/units, also recommends !init add commands.

    Accepted monster item formats:
        {"name": "Goblin", "count": 2}
        {"monster_name": "Goblin", "count": 2}
    """

    def handle(self, event: GameEvent) -> Optional[List[Dict[str, Any]]]:
        if event.type != EventTypes.COMBAT_START:
            return None

        commands: List[Dict[str, Any]] = [
            {
                "type": "suggested_command",
                "system": "AVRAE",
                "command": "!init begin",
                "reason": str(event.payload.get("source") or "combat_start"),
                "requires_dm_confirmation": True,
            }
        ]

        for monster in self._extract_monsters(event.payload):
            name = monster["name"]
            count = monster["count"]
            commands.append(
                {
                    "type": "suggested_command",
                    "system": "AVRAE",
                    "command": f"!init add {name} {count}",
                    "reason": "combat_start_monster_add",
                    "requires_dm_confirmation": True,
                }
            )

        return commands

    @staticmethod
    def _extract_monsters(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_units = payload.get("monsters") or payload.get("units") or []
        monsters: List[Dict[str, Any]] = []

        for item in raw_units:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("monster_name") or "").strip()
            if not name:
                continue
            try:
                count = int(item.get("count", 1))
            except (TypeError, ValueError):
                count = 1
            monsters.append({"name": name, "count": max(1, count)})

        return monsters
