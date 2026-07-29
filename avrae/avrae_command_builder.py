"""
AVRAE/AVRAE_COMMAND_BUILDER.PY
Converts resolved encounter/check/damage data into Avrae command strings.

This implementation produces flag-based !init madd invocations and
Avrae-compatible save/check/damage commands per avrae.io/commands.

C3 boundary rule:
Formatting only. No Discord I/O, no HTTP calls, no Avrae dispatch, and no
combat/game-state mutation here. Callers must display these commands as
DM-facing suggestions unless an explicitly experimental adapter is used.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from core.encounter_models import EncounterResult


class AvraeCommandBuilder:
    @staticmethod
    def _quote_if_needed(value: str) -> str:
        v = str(value or "")
        if " " in v or '"' in v:
            # escape existing quotes and wrap in double quotes
            safe = v.replace('"', '\\"')
            return f'"{safe}"'
        return v

    @staticmethod
    def _render_madd_flags(monster: Dict[str, Any]) -> str:
        """
        Render flags for !init madd from a monster dict.
        Supported keys (if present):
          name, n, h (bool), p, controller, group, adv (bool), dis (bool),
          b (bonus), initscore (bool), rollhp (bool), hp, thp, ac, note
        """
        parts: List[str] = []
        name = str(monster.get("name") or monster.get("monster_name") or "").strip()
        if name:
            parts.append(f"-name {AvraeCommandBuilder._quote_if_needed(name)}")

        # count / dice: -n accepts number or dice string like 2d4
        n = monster.get("count") or monster.get("n")
        if n is not None:
            parts.append(f"-n {str(n)}")

        # hide hp/ac/etc. include -h when explicitly true
        hide = monster.get("h")
        if hide is True:
            parts.append("-h")

        # placement / position override
        p = monster.get("p")
        if p is not None:
            parts.append(f"-p {str(p)}")

        controller = monster.get("controller")
        if controller:
            parts.append(f"-controller {AvraeCommandBuilder._quote_if_needed(controller)}")

        group = monster.get("group")
        if group:
            parts.append(f"-group {AvraeCommandBuilder._quote_if_needed(group)}")

        # advantage/disadvantage flags
        if monster.get("adv"):
            parts.append("adv")
        if monster.get("dis"):
            parts.append("dis")

        # initiative bonus
        b = monster.get("b")
        if b is not None:
            parts.append(f"-b {str(b)}")

        # initscore / rollhp
        if monster.get("initscore"):
            parts.append("initscore")
        if monster.get("rollhp"):
            parts.append("rollhp")

        # explicit hp/thp/ac
        if monster.get("hp") is not None:
            parts.append(f"-hp {str(monster.get('hp'))}")
        if monster.get("thp") is not None:
            parts.append(f"-thp {str(monster.get('thp'))}")
        if monster.get("ac") is not None:
            parts.append(f"-ac {str(monster.get('ac'))}")

        note = monster.get("note")
        if note:
            # note may contain pipes/newlines; wrap in quotes
            parts.append(f"-note {AvraeCommandBuilder._quote_if_needed(note)}")

        return " ".join(parts)

    @staticmethod
    def build_init_commands(encounter: EncounterResult) -> List[str]:
        commands: List[str] = ["!init begin"]
        for unit in encounter.units:
            # Build a single madd invocation using flags when we have structured data
            # unit.monster_name, unit.count, and potential metadata are expected.
            monster = {"name": unit.monster_name, "n": unit.count}
            flags = AvraeCommandBuilder._render_madd_flags(monster)
            commands.append(f"!init madd {flags}".strip())
        return commands

    @staticmethod
    def build_init_commands_from_monsters(monsters: Iterable[Dict[str, Any]]) -> List[str]:
        """
        Accepts iterables of dicts that may include any of the supported flags.
        If a dict has count > 1 and the name contains '#', Avrae will auto-number.
        """
        commands: List[str] = ["!init begin"]
        for monster in monsters or []:
            name = str(monster.get("name") or monster.get("monster_name") or "").strip()
            if not name and not monster.get("n"):
                continue
            # ensure name is present for madd -name usage
            if name:
                monster.setdefault("name", name)
            flags = AvraeCommandBuilder._render_madd_flags(monster)
            commands.append(f"!init madd {flags}".strip())
        return commands

    @staticmethod
    def build_check_command(check: str, dc: int | None = None, is_save: bool = False) -> str:
        """
        Build a save or check command.
        - For saves we emit: !save <ability> [-dc N]
        - For checks we emit: !check <skill> [-dc N]
        Prefer -dc form since it's explicit and listed in the doc.
        """
        normalized = str(check or "").strip()
        if not normalized:
            return ""
        dc_part = ""
        if dc is not None and int(dc) > 0:
            dc_part = f" -dc {int(dc)}"
        if is_save or normalized.lower().endswith("save"):
            # normalize ability name for save (strip the word 'save' if present)
            ability = normalized.lower().replace("save", "").strip() or normalized
            return f"!save {ability}{dc_part}".strip()
        return f"!check {normalized}{dc_part}".strip()

    @staticmethod
    def build_damage_command(target: str, amount: int | str, damage_type: Optional[str] = None) -> str:
        """
        Build !damage command.
        Supports multiple targets (comma-separated) in target string.
        Damage type is appended as a normal token if present.
        Examples:
          !damage goblin1 7 slashing
          !damage t1,t2 10 fire
        """
        safe_target = str(target or "PLAYER")
        safe_amount = str(amount or 0).strip() or "0"
        if damage_type:
            return f"!damage {safe_target} {safe_amount} {str(damage_type).strip()}"
        return f"!damage {safe_target} {safe_amount}"
