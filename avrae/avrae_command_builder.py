"""
AVRAE/AVRAE_COMMAND_BUILDER.PY
Converts resolved encounter/check/damage data into Avrae command strings.

C3 boundary rule:
Formatting only. No Discord I/O, no HTTP calls, no Avrae dispatch, and no
combat/game-state mutation here. Callers must display these commands as
DM-facing suggestions unless an explicitly experimental adapter is used.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.encounter_models import EncounterResult


class AvraeCommandBuilder:
    @staticmethod
    def build_init_commands(encounter: EncounterResult) -> List[str]:
        commands: List[str] = ["!init begin"]
        for unit in encounter.units:
            # Use !init madd for multiple monsters
            if unit.count > 1:
                # Wrap monster name in quotes if it contains spaces
                monster_name = f'"{unit.monster_name}"' if ' ' in unit.monster_name else unit.monster_name
                commands.append(f"!init madd {monster_name} -n {unit.count}")
            else:
                commands.append(f"!init add {unit.monster_name}")
        return commands

    @staticmethod
    def build_init_commands_from_monsters(monsters: Iterable[Dict[str, Any]]) -> List[str]:
        commands: List[str] = ["!init begin"]
        for monster in monsters or []:
            name = str(monster.get("name") or monster.get("monster_name") or "").strip()
            if not name:
                continue
            try:
                count = int(monster.get("count", 1))
            except (TypeError, ValueError):
                count = 1
            # Use !init madd for multiple monsters
            if count > 1:
                # Wrap monster name in quotes if it contains spaces
                monster_name = f'"{name}"' if ' ' in name else name
                commands.append(f"!init madd {monster_name} -n {count}")
            else:
                commands.append(f"!init add {name}")
        return commands

    @staticmethod
    def build_check_command(check: str, dc: int) -> str:
        normalized = str(check or "").strip()
        if not normalized or normalized.lower() == "none" or int(dc or 0) <= 0:
            return ""

        lower = normalized.lower()
        if "save" in lower:
            ability = lower.replace("save", "").strip() or "dex"
            return f"!save {ability} dc {int(dc)}"
        return f"!check {normalized} dc {int(dc)}"

    @staticmethod
    def build_damage_command(target: str, amount: int | str, damage_type: str | None = None) -> str:
        safe_target = str(target or "PLAYER")
        safe_amount = str(amount or 0).strip() or "0"
        suffix = f"[{damage_type}]" if damage_type else ""
        return f"!damage {safe_target} {safe_amount}{suffix}"
