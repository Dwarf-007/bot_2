"""
SERVICES/TRAP_EVENT_MAPPER.PY
Maps trap evaluation results to canonical GameEvents and Avrae-ready effects.
"""

from __future__ import annotations

from typing import List

from core.game_events import EventTypes, GameEvent
from core.trap_consequence_models import TrapEvaluationBundle


class TrapEventMapper:
    def map_bundle_to_events(self, bundle: TrapEvaluationBundle) -> List[GameEvent]:
        events: List[GameEvent] = []
        for result in bundle.triggered_results:
            events.append(
                GameEvent(
                    EventTypes.TRAP_TRIGGERED,
                    {
                        "room_id": bundle.room_id,
                        "trap_name": result.trap_name,
                        "narrative_hint": result.narrative_hint,
                    },
                )
            )

            if result.required_check and result.required_check.lower() != "none" and result.dc > 0:
                events.append(
                    GameEvent(
                        EventTypes.REQUIRED_CHECK,
                        {
                            "room_id": bundle.room_id,
                            "source": result.trap_name,
                            "check": result.required_check,
                            "dc": result.dc,
                        },
                    )
                )

            if result.damage > 0:
                events.append(
                    GameEvent(
                        EventTypes.DAMAGE,
                        {
                            "room_id": bundle.room_id,
                            "amount": result.damage,
                            "type": result.damage_type,
                            "source": result.trap_name,
                        },
                    )
                )

            if "combat" in {tag.lower() for tag in result.effect_tags}:
                events.append(
                    GameEvent(
                        EventTypes.COMBAT_START,
                        {
                            "room_id": bundle.room_id,
                            "source": result.trap_name,
                        },
                    )
                )
        return events
