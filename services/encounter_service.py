"""
SERVICES/ENCOUNTER_SERVICE.PY
High-level encounter orchestration helper.

Responsibilities:
- Determine encounter difficulty.
- Resolve a concrete encounter from room data.
- Register optional combat feedback tracking.
- Produce DM-facing suggested Avrae init commands for TurnOutput.

No Discord I/O here.
No Avrae dispatch here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from avrae.avrae_command_builder import AvraeCommandBuilder
from core.encounter_models import EncounterResult, EncounterUnit
from core.encounter_policy import determine_difficulty
from core.encounter_resolver import EncounterResolver
from core.turn_output import TurnOutput


class EncounterService:
    def __init__(
        self,
        resolver: Optional[EncounterResolver] = None,
        command_builder: Optional[AvraeCommandBuilder] = None,
        combat_feedback_service=None,
    ) -> None:
        self.resolver = resolver or EncounterResolver()
        # Formatter/helper only. It must not dispatch commands.
        self.command_builder = command_builder or AvraeCommandBuilder()
        self.combat_feedback_service = combat_feedback_service

    def prepare_room_encounter(
        self,
        channel_id: str,
        room_id: Optional[str],
        room_data: Dict[str, Any],
        party_level: int,
        player_count: int,
        scaling_enabled: bool = True,
        encounter_type: str = "STATIC_ROOM",
        room_danger_rating: Optional[int] = None,
        xp_reward_total: int = 0,
    ) -> TurnOutput:
        difficulty = determine_difficulty(
            party_level=party_level,
            player_count=player_count,
            scaling_enabled=scaling_enabled,
            encounter_type=encounter_type,
            room_danger_rating=room_danger_rating,
        )

        encounter = self._resolve_encounter(
            room_data=room_data,
            difficulty=difficulty,
            encounter_type=encounter_type,
            room_id=room_id,
        )
        return self.prepare_resolved_encounter(
            channel_id=channel_id,
            encounter=encounter,
            xp_reward_total=xp_reward_total,
        )

    def prepare_resolved_encounter(
        self,
        channel_id: str,
        encounter: EncounterResult,
        xp_reward_total: int = 0,
    ) -> TurnOutput:
        output = TurnOutput()
        if not encounter.units:
            output.debug_notes.append("Encounter has no units; no suggested Avrae commands generated.")
            return output

        output.dm_instructions.extend([
            "Encounter előkészítve. Az AI-DM nem küldi el automatikusan az Avrae parancsokat.",
            "Ha Avrae-t használtok, a DM manuálisan adja ki az alábbi javasolt parancsokat.",
        ])
        output.suggested_commands.extend(self.command_builder.build_init_commands(encounter))
        output.debug_notes.append(
            f"Encounter prepared: {encounter.encounter_type}, difficulty={encounter.difficulty}"
        )

        if self.combat_feedback_service:
            self.combat_feedback_service.register_encounter(
                channel_id=str(channel_id),
                room_id=encounter.room_id,
                monsters=self._units_to_monsters(encounter.units),
                xp_reward_total=int(xp_reward_total or 0),
            )
            output.debug_notes.append("Combat feedback tracking registered as optional inbound adapter.")

        return output

    def _resolve_encounter(
        self,
        room_data: Dict[str, Any],
        difficulty: str,
        encounter_type: str,
        room_id: Optional[str],
    ) -> EncounterResult:
        """
        Adapter around EncounterResolver.

        Existing resolver implementations may differ during refactor. This method
        first tries the expected resolver API and then falls back to room_data
        monsters if needed.
        """

        if hasattr(self.resolver, "resolve"):
            try:
                return self.resolver.resolve(
                    room_data=room_data,
                    difficulty=difficulty,
                    encounter_type=encounter_type,
                    room_id=room_id,
                )
            except TypeError:
                pass

        units = []
        for monster in room_data.get("monsters", []) or []:
            name = str(monster.get("name") or monster.get("monster_name") or "").strip()
            if not name:
                continue
            try:
                count = int(monster.get("count", 1))
            except (TypeError, ValueError):
                count = 1
            units.append(EncounterUnit(monster_name=name, count=max(1, count), source="ROOM"))

        return EncounterResult(
            encounter_type=encounter_type,
            difficulty=difficulty,
            units=units,
            room_id=room_id,
            trigger_reason="room_monsters_fallback",
            narrative_hint="Harc kezdődik.",
        )

    @staticmethod
    def _units_to_monsters(units: List[EncounterUnit]) -> List[Dict[str, Any]]:
        return [
            {"name": unit.monster_name, "count": unit.count}
            for unit in units
            if unit.monster_name and unit.count > 0
        ]
