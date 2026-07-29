"""
SERVICES/TRAP_DEFINITION_PARSER.PY
Extracts trap definitions from room data.

Preferred source: room_data["traps"] as structured JSON/list.
Fallback source: lightweight regex heuristics over room_data["facts"].
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.trap_consequence_models import TrapDefinition


class TrapDefinitionParser:
    def parse_room_traps(self, room_data: Dict[str, Any]) -> List[TrapDefinition]:
        structured = room_data.get("traps") or room_data.get("trap_definitions") or []
        traps = self._parse_structured_traps(structured)
        if traps:
            return traps
        return self._parse_facts_for_trap(room_data.get("facts", ""))

    def _parse_structured_traps(self, raw_traps: Any) -> List[TrapDefinition]:
        if not isinstance(raw_traps, list):
            return []

        traps: List[TrapDefinition] = []
        for index, item in enumerate(raw_traps, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or f"trap_{index}").strip()
            trigger_on = item.get("trigger_on") or item.get("triggers") or ["exit_failure"]
            effect_tags = item.get("effect_tags") or item.get("effects") or []
            traps.append(
                TrapDefinition(
                    name=name,
                    trigger_on=[str(value) for value in trigger_on] if isinstance(trigger_on, list) else [str(trigger_on)],
                    damage=self._safe_int(item.get("damage"), 0),
                    damage_type=str(item.get("damage_type") or ""),
                    required_check=str(item.get("required_check") or "None"),
                    dc=self._safe_int(item.get("dc"), 0),
                    effect_tags=[str(value) for value in effect_tags] if isinstance(effect_tags, list) else [str(effect_tags)],
                    once=bool(item.get("once", True)),
                    description=str(item.get("description") or ""),
                )
            )
        return traps

    def _parse_facts_for_trap(self, facts: str) -> List[TrapDefinition]:
        text = str(facts or "")
        lower = text.lower()
        if "trap" not in lower and "csapda" not in lower:
            return []

        dc = self._extract_dc(text)
        damage = self._extract_damage(text)
        damage_type = self._extract_damage_type(text)
        tags = ["damage"] if damage > 0 else []
        if "combat" in lower or "monster" in lower or "szörny" in lower:
            tags.append("combat")

        return [
            TrapDefinition(
                name="room_trap",
                trigger_on=["exit_failure", "forced_entry", "open", "search_failure"],
                damage=damage,
                damage_type=damage_type,
                required_check="Dexterity Save" if damage > 0 else "None",
                dc=dc,
                effect_tags=tags,
                once=True,
                description=text[:300],
            )
        ]

    @staticmethod
    def _extract_dc(text: str) -> int:
        match = re.search(r"\bDC\s*(\d{1,2})\b", text, flags=re.IGNORECASE)
        return int(match.group(1)) if match else 13

    @staticmethod
    def _extract_damage(text: str) -> int:
        # MVP deterministic default: use average-ish value from first NdM expression if present.
        match = re.search(r"\b(\d+)d(\d+)\b", text, flags=re.IGNORECASE)
        if not match:
            return 0
        count = int(match.group(1))
        sides = int(match.group(2))
        return max(1, count * ((sides + 1) // 2))

    @staticmethod
    def _extract_damage_type(text: str) -> str:
        lower = text.lower()
        for damage_type in ["piercing", "slashing", "bludgeoning", "fire", "poison", "acid", "cold", "necrotic"]:
            if damage_type in lower:
                return damage_type
        return ""

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
