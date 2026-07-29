"""
SERVICES/REST_SERVICE.PY
Application service for short/long rest handling.

Rest is deterministic at the engine level. Avrae may still be used by players for
character-sheet rest automation if desired, but the AI DM engine decides whether
the rest succeeds, is denied, or is interrupted by an encounter.
"""

from __future__ import annotations

from typing import Optional

from core.game_constants import DEFAULT_ENCOUNTER_SCALING_ENABLED, DEFAULT_PARTY_LEVEL
from core.game_events import EventBus, EventTypes, GameEvent
from core.rest_models import RestPolicy, RestResolution
from core.turn_output import TurnOutput
from services.rest_intent_service import RestIntentService
from services.rest_policy_service import RestPolicyService


class RestService:
    def __init__(
        self,
        channel_repo,
        location_repo,
        event_bus: EventBus,
        encounter_service=None,
        intent_service: Optional[RestIntentService] = None,
        policy_service: Optional[RestPolicyService] = None,
        default_policy: Optional[RestPolicy] = None,
    ) -> None:
        self.channel_repo = channel_repo
        self.location_repo = location_repo
        self.event_bus = event_bus
        self.encounter_service = encounter_service
        self.intent_service = intent_service or RestIntentService()
        self.policy_service = policy_service or RestPolicyService()
        self.default_policy = default_policy or RestPolicy(default_ambush_monster="Goblin", default_ambush_xp=50)

    def try_handle_rest(self, channel_id: str, player_id: str, text: str) -> Optional[TurnOutput]:
        intent = self.intent_service.detect(text)
        if not intent.requested:
            return None

        state = self.channel_repo.get_state(channel_id)
        room_id = state.get("current_location_id")
        room_data = self.location_repo.get_room(room_id) if room_id else None
        resolution = self.policy_service.resolve_rest(intent.rest_type, room_data or {}, self.default_policy)
        return self._build_output(channel_id, resolution, room_id)

    def _build_output(self, channel_id: str, resolution: RestResolution, room_id: str | None) -> TurnOutput:
        self.event_bus.emit(
            GameEvent(EventTypes.REST_REQUESTED, {"channel_id": str(channel_id), "rest_type": resolution.rest_type, "room_id": room_id})
        )

        if resolution.status == "DENIED":
            return TurnOutput(public_narrative=self._denied_text(resolution), debug_notes=[resolution.reason])

        if resolution.status == "SUCCESS":
            self.event_bus.emit(
                GameEvent(EventTypes.REST_COMPLETED, {"channel_id": str(channel_id), "rest_type": resolution.rest_type, "room_id": room_id})
            )
            return TurnOutput(public_narrative=self._success_text(resolution), debug_notes=[resolution.reason])

        if resolution.status == "INTERRUPTED":
            self.event_bus.emit(
                GameEvent(
                    EventTypes.REST_INTERRUPTED,
                    {
                        "channel_id": str(channel_id),
                        "rest_type": resolution.rest_type,
                        "room_id": room_id,
                        "reason": resolution.reason,
                    },
                )
            )
            output = TurnOutput(public_narrative=self._interrupted_text(resolution), debug_notes=[resolution.reason])
            if self.encounter_service and resolution.ambush_monsters:
                encounter_output = self.encounter_service.prepare_room_encounter(
                    channel_id=channel_id,
                    room_id=room_id,
                    room_data={"monsters": resolution.ambush_monsters},
                    party_level=DEFAULT_PARTY_LEVEL,
                    player_count=max(1, len(self.channel_repo.get_state(channel_id).players)),
                    scaling_enabled=DEFAULT_ENCOUNTER_SCALING_ENABLED,
                    encounter_type="REST_AMBUSH",
                    xp_reward_total=resolution.xp_reward_total,
                )
                output.avrae_commands.extend(encounter_output.avrae_commands)
                output.debug_notes.extend(encounter_output.debug_notes)
            return output

        return TurnOutput(public_narrative="Nem sikerül egyértelműen kezelni a pihenést.", debug_notes=[resolution.reason])

    @staticmethod
    def _success_text(resolution: RestResolution) -> str:
        if resolution.rest_type == "LONG":
            return "A csapat hosszú pihenőt tart. Az órák lassan telnek, de a pihenés zavartalanul lezajlik."
        return "A csapat rövid pihenőt tart. Van idő levegőhöz jutni, kötéseket igazítani és rendezni a sorokat."

    @staticmethod
    def _interrupted_text(resolution: RestResolution) -> str:
        if resolution.rest_type == "LONG":
            return "A hosszú pihenőt zaj, mozgás vagy közeledő veszély szakítja félbe. Harci helyzet alakul ki!"
        return "A rövid pihenő nem marad zavartalan. Valami megzavarja a csendet — harci helyzet alakul ki!"

    @staticmethod
    def _denied_text(resolution: RestResolution) -> str:
        if resolution.rest_type == "LONG":
            return "Itt most nem tűnik biztonságosnak hosszú pihenőt tartani."
        return "Itt most nem tűnik biztonságosnak rövid pihenőt tartani."
