"""
SERVICES/TRAP_RESOLUTION_SERVICE.PY
Application service that evaluates traps and converts them into TurnOutput.
"""

from __future__ import annotations

from typing import Optional

from avrae.avrae_command_builder import AvraeCommandBuilder
from core.game_events import EventBus, EventTypes, GameEvent
from core.trap_consequence_models import TrapTriggerContext
from core.turn_output import TurnOutput
from services.trap_event_mapper import TrapEventMapper
from services.trap_failure_consequence_engine import TrapFailureConsequenceEngine


class TrapResolutionService:
    def __init__(
        self,
        channel_repo,
        location_repo,
        event_bus: EventBus,
        trap_engine: Optional[TrapFailureConsequenceEngine] = None,
        mapper: Optional[TrapEventMapper] = None,
        command_builder: Optional[AvraeCommandBuilder] = None,
    ) -> None:
        self.channel_repo = channel_repo
        self.location_repo = location_repo
        self.event_bus = event_bus
        self.trap_engine = trap_engine or TrapFailureConsequenceEngine()
        self.mapper = mapper or TrapEventMapper()
        self.command_builder = command_builder or AvraeCommandBuilder()

    def evaluate_movement_failure(
        self,
        channel_id: str,
        room_id: str,
        attempted_direction: Optional[str],
        failure_reason: str,
        player_id: Optional[str] = None,
        action_text: str = "",
    ) -> TurnOutput:
        state = self.channel_repo.get_state(channel_id)
        room_data = self.location_repo.get_room(room_id) or {"room_id": room_id, "facts": ""}
        context = TrapTriggerContext(
            room_id=str(room_id),
            attempted_direction=attempted_direction,
            failure_reason=failure_reason,
            player_id=player_id,
            action_text=action_text,
        )
        bundle = self.trap_engine.evaluate_exit_failure_traps_stateful(
            room_data=room_data,
            context=context,
            trap_state=state.get("trap_state", {}),
        )

        if not bundle.triggered_results:
            return TurnOutput(debug_notes=bundle.debug_notes)

        self.channel_repo.update_field(channel_id, "trap_state", bundle.updated_trap_state)
        events = self.mapper.map_bundle_to_events(bundle)
        output = TurnOutput()
        output.debug_notes.extend(bundle.debug_notes)

        narrative_lines = []
        for result in bundle.triggered_results:
            narrative_lines.append(result.narrative_hint or f"Csapda aktiválódik: {result.trap_name}")

        for event in events:
            self.event_bus.emit(event)
            if event.type == EventTypes.REQUIRED_CHECK:
                check = event.payload.get("check", "None")
                dc = int(event.payload.get("dc", 0) or 0)
                command = self.command_builder.build_check_command(check, dc)
                if command:
                    output.avrae_commands.append(command)
            elif event.type == EventTypes.DAMAGE:
                output.avrae_commands.append(
                    self.command_builder.build_damage_command(
                        target="PLAYER",
                        amount=event.payload.get("amount", 0),
                        damage_type=event.payload.get("type") or None,
                    )
                )
            elif event.type == EventTypes.COMBAT_START:
                output.avrae_commands.append("!init begin")

        output.public_narrative = "\n".join(narrative_lines)
        return output
