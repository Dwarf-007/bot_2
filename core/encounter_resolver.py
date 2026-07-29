
"""
ENCOUNTER_RESOLVER.PY - Pure encounter resolution logic.

Responsibilities:
- Resolve a concrete encounter from room data + policy inputs
- Expand simple dice notation for counts via core.encounter_logic
- Return EncounterResult without side effects
"""

from typing import Any, Dict, List, Optional

from core.encounter_logic import roll_dice_string
from core.encounter_models import EncounterResult, EncounterUnit


_DIFFICULTY_DEFAULT_COUNTS = {
    "EASY": 1,
    "STANDARD": 2,
    "HARD": 3,
    "DEADLY": 4,
}


class EncounterResolver:
    """
    Pure domain resolver for concrete encounters.
    """

    @staticmethod
    def resolve_static_room_encounter(
        room_id: Optional[str],
        room_data: Dict[str, Any],
        difficulty: str,
    ) -> EncounterResult:
        """
        Resolves a room-based static encounter from room monster definitions.
        """
        units = EncounterResolver._units_from_room_monsters(
            monsters=room_data.get("monsters", []),
            difficulty=difficulty,
            source="ROOM",
        )

        if not units:
            units = [EncounterUnit(monster_name="Goblin", count=1, source="FALLBACK")]

        return EncounterResult(
            encounter_type="STATIC_ROOM",
            difficulty=difficulty,
            units=units,
            room_id=room_id,
            trigger_reason="Room contains hostile entities.",
            narrative_hint="Hostile movement emerges from the darkness.",
        )

    @staticmethod
    def resolve_rest_ambush(
        room_id: Optional[str],
        room_data: Dict[str, Any],
        difficulty: str,
    ) -> EncounterResult:
        """
        Resolves a rest interruption ambush encounter.
        """
        units = EncounterResolver._units_from_room_monsters(
            monsters=room_data.get("monsters", []),
            difficulty=difficulty,
            source="ROOM",
        )

        if not units:
            fallback_count = _DIFFICULTY_DEFAULT_COUNTS.get(difficulty, 2)
            units = [EncounterUnit(monster_name="Goblin", count=fallback_count, source="FALLBACK")]

        return EncounterResult(
            encounter_type="REST_AMBUSH",
            difficulty=difficulty,
            units=units,
            room_id=room_id,
            trigger_reason="Rest interrupted in unsafe location.",
            narrative_hint="The party is jolted awake by hostile movement.",
        )

    @staticmethod
    def _units_from_room_monsters(
        monsters: List[Any],
        difficulty: str,
        source: str,
    ) -> List[EncounterUnit]:
        """
        Converts room monster definitions into normalized encounter units.

        Supported inputs:
        - ["Goblin", "Skeleton"]
        - [{"monster_name": "Goblin", "count": "1d4"}]
        - [{"name": "Goblin", "count": 2}]
        """
        if not monsters:
            return []

        normalized_units: List[EncounterUnit] = []
        default_count = _DIFFICULTY_DEFAULT_COUNTS.get(difficulty, 2)

        for monster_entry in monsters:
            if isinstance(monster_entry, str):
                normalized_units.append(
                    EncounterUnit(
                        monster_name=monster_entry,
                        count=default_count,
                        source=source,
                    )
                )
                continue

            if isinstance(monster_entry, dict):
                monster_name = str(
                    monster_entry.get("monster_name")
                    or monster_entry.get("name")
                    or "Goblin"
                )
                raw_count = monster_entry.get("count", default_count)
                resolved_count = EncounterResolver._resolve_count(raw_count, default_count)
                normalized_units.append(
                    EncounterUnit(
                        monster_name=monster_name,
                        count=resolved_count,
                        source=source,
                    )
                )

        return [unit for unit in normalized_units if unit.count > 0]

    @staticmethod
    def _resolve_count(raw_count: Any, default_count: int) -> int:
        """
        Expands integer or dice-string counts into a concrete positive value.
        """
        if isinstance(raw_count, int):
            return max(1, raw_count)

        if isinstance(raw_count, str):
            normalized = raw_count.strip()
            if normalized:
                return max(1, roll_dice_string(normalized))

        return max(1, int(default_count))

