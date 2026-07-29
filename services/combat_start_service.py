"""
SERVICES/COMBAT_START_SERVICE.PY
Small application service for explicit combat starts.

This is useful when combat comes from LLM response, trap consequence, admin
command, or deterministic room logic.

C3.5 update:
- Explicit combat starts return DM-facing advisory output.
- Avrae commands are expected in TurnOutput.suggested_commands, not dispatched.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.encounter_models import EncounterResult, EncounterUnit
from core.turn_output import TurnOutput
from services.encounter_service import EncounterService


class CombatStartService:
    def __init__(self, encounter_service: EncounterService) -> None:
        self.encounter_service = encounter_service

    def start_combat(
        self,
        channel_id: str,
        room_id: Optional[str],
        monsters: List[Dict[str, Any]],
        difficulty: str = "STANDARD",
        encounter_type: str = "MANUAL",
        xp_reward_total: int = 0,
        narrative: str = "Harci helyzet alakul ki!",
    ) -> TurnOutput:
        units = []
        for monster in monsters or []:
            name = str(monster.get("name") or monster.get("monster_name") or "").strip()
            if not name:
                continue
            try:
                count = int(monster.get("count", 1))
            except (TypeError, ValueError):
                count = 1
            units.append(EncounterUnit(monster_name=name, count=max(1, count), source="MANUAL"))

        encounter = EncounterResult(
            encounter_type=encounter_type,
            difficulty=difficulty,
            units=units,
            room_id=room_id,
            trigger_reason="explicit_combat_start",
            narrative_hint=narrative,
        )
        output = self.encounter_service.prepare_resolved_encounter(
            channel_id=channel_id,
            encounter=encounter,
            xp_reward_total=xp_reward_total,
        )
        output.public_narrative = narrative

        if output.suggested_commands and not output.dm_instructions:
            output.dm_instructions.extend([
                "A DM manuálisan adja ki az alábbi javasolt Avrae parancsokat.",
                "Az AI-DM nem hajt végre automatikus Avrae dispatch-et.",
            ])
        elif output.suggested_commands:
            output.dm_instructions.append("A javasolt parancsok nem futnak automatikusan; DM copy/paste szükséges.")

        output.debug_notes.append("CombatStartService used advisory suggested_commands output.")
        return output
