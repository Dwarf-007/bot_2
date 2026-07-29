
"""
SERVICES/MOVEMENT_SERVICE.PY
Application service for deterministic player movement, with trap hook and alias-aware target fallback.
"""

from __future__ import annotations

from typing import Optional

from core.game_events import EventBus, EventTypes, GameEvent
from core.room_graph_models import MovementIntent, MovementResult
from core.turn_output import TurnOutput
from services.movement_intent_service import MovementIntentService
from services.navigation_engine import NavigationEngine
from services.room_graph_builder import RoomGraphBuilder


class MovementService:
    def __init__(
        self,
        channel_repo,
        location_repo,
        event_bus: EventBus,
        graph_builder: Optional[RoomGraphBuilder] = None,
        intent_service: Optional[MovementIntentService] = None,
        trap_resolution_service=None,
        room_alias_service=None,
    ) -> None:
        self.channel_repo = channel_repo
        self.location_repo = location_repo
        self.event_bus = event_bus
        self.graph_builder = graph_builder or RoomGraphBuilder()
        self.intent_service = intent_service or MovementIntentService()
        self.navigation_engine = NavigationEngine()
        self.trap_resolution_service = trap_resolution_service
        self.room_alias_service = room_alias_service

    def refresh_graph(self, campaign_id: str | None = None) -> None:
        graph = self.graph_builder.build_from_location_repository(self.location_repo, campaign_id=campaign_id)
        self.navigation_engine.set_graph(graph)

    def detect_intent(self, text: str) -> MovementIntent:
        return self.intent_service.detect(text)

    def try_handle_movement(self, channel_id: str, text: str, player_id: str | None = None) -> Optional[TurnOutput]:
        intent = self.detect_intent(text)
        if not intent.requested:
            return None

        state = self.channel_repo.get_state(channel_id)
        campaign_id = str(state.get("campaign_id") or "default")
        self.refresh_graph(campaign_id=campaign_id)
        current_room_id = state.get("current_location_id")

        if intent.direction:
            result = self.navigation_engine.try_move(current_room_id, intent.direction)
        else:
            target = self.navigation_engine.find_room_by_title_hint(intent.target_room_hint or "")
            if not target and self.room_alias_service:
                target = self.room_alias_service.resolve_room_id(campaign_id, intent.target_room_hint or "")
            direction = self.navigation_engine.direction_to(current_room_id, target) if target else None
            result = self.navigation_engine.try_move(current_room_id, direction)

        return self._build_output(channel_id, result, player_id=player_id, action_text=text)

    def validate_next_room(self, current_room_id: str | None, next_room_id: str | None) -> bool:
        state_campaign = None
        self.refresh_graph(campaign_id=state_campaign)
        return self.navigation_engine.is_adjacent(current_room_id, next_room_id)

    def _build_output(self, channel_id: str, result: MovementResult, player_id: str | None = None, action_text: str = "") -> TurnOutput:
        if not result.success:
            trap_output = self._try_trap_on_failure(channel_id, result, player_id, action_text)
            base_narrative = self._failure_narrative(result)
            if trap_output:
                trap_output.public_narrative = f"{base_narrative}\n{trap_output.public_narrative}" if trap_output.public_narrative else base_narrative
                trap_output.debug_notes.append(f"movement_failed:{result.reason}")
                return trap_output
            return TurnOutput(public_narrative=base_narrative, debug_notes=[f"movement_failed:{result.reason}"])

        self.channel_repo.set_location(channel_id, result.to_room_id)
        room = self.location_repo.get_room(result.to_room_id) if result.to_room_id else None
        title = room.get("title") if room else result.to_room_id
        facts = room.get("facts", "") if room else ""
        narrative = f"A csapat továbbhalad {self._direction_label(result.direction)} irányba.\n**{title}**"
        if facts:
            narrative += f"\n{facts[:600]}"
        self.event_bus.emit(GameEvent(EventTypes.PLAYER_MOVED, {"channel_id": str(channel_id), "from_room": result.from_room_id, "to_room": result.to_room_id, "direction": result.direction}))
        return TurnOutput(public_narrative=narrative, state_changed=True, next_room_id=result.to_room_id)

    def _try_trap_on_failure(self, channel_id: str, result: MovementResult, player_id: str | None, action_text: str) -> Optional[TurnOutput]:
        if not self.trap_resolution_service or not result.from_room_id:
            return None
        return self.trap_resolution_service.evaluate_movement_failure(channel_id=channel_id, room_id=result.from_room_id, attempted_direction=result.direction, failure_reason=result.reason, player_id=player_id, action_text=action_text)

    @staticmethod
    def _failure_narrative(result: MovementResult) -> str:
        if result.reason == "no_current_room":
            return "Még nincs beállítva aktuális helyszín ehhez a csatornához."
        if result.reason == "exit_not_found":
            return "Arra nem látszik járható kijárat."
        if result.reason == "target_room_not_found":
            return "A kijárat egy ismeretlen vagy még be nem töltött helyszínre mutat."
        if result.reason == "current_room_not_found":
            return "Az aktuális helyszín nem található a betöltött térképen."
        return "Nem sikerül egyértelműen meghatározni az útvonalat."

    @staticmethod
    def _direction_label(direction: str | None) -> str:
        labels = {"north": "észak", "south": "dél", "east": "kelet", "west": "nyugat", "up": "felfelé", "down": "lefelé", "in": "befelé", "out": "kifelé"}
        return labels.get(str(direction), str(direction or "ismeretlen"))
