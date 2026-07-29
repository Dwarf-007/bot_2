"""
SERVICES/STORY_ENGINE.PY
Applies normalized LLMResponse to deterministic game state and builds TurnOutput.
Now validates LLM-proposed next_room_id through MovementService when available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.game_constants import DEFAULT_ENCOUNTER_SCALING_ENABLED, DEFAULT_PARTY_LEVEL
from core.game_events import EventBus, EventTypes, GameEvent
from core.llm_response import LLMResponse
from core.turn_output import TurnOutput


class StoryEngine:
    def __init__(
        self,
        channel_repo,
        inventory_repo=None,
        player_repo=None,
        location_repo=None,
        event_bus: Optional[EventBus] = None,
        encounter_service=None,
        movement_service=None,
    ) -> None:
        self.channel_repo = channel_repo
        self.inventory_repo = inventory_repo
        self.player_repo = player_repo
        self.location_repo = location_repo
        self.event_bus = event_bus or EventBus()
        self.encounter_service = encounter_service
        self.movement_service = movement_service

    def apply(self, channel_id: str, player_id: str, response: LLMResponse, active_players: Optional[List[str]] = None) -> TurnOutput:
        active_players = active_players or [str(player_id)]
        output = TurnOutput(public_narrative=response.narrative or "")
        output.secret_messages.extend(response.secret_messages)
        output.debug_notes.extend(response.dm_notes)

        self._apply_room_transition(channel_id, response, output)
        self._apply_required_check(channel_id, response, output)
        self._apply_damage(response, output)
        self._apply_combat_start(channel_id, response, output)
        self._apply_inventory(channel_id, player_id, response, output)
        self._apply_xp(channel_id, active_players, response, output)
        self._apply_rest(channel_id, response, output)
        return output

    def _apply_room_transition(self, channel_id: str, response: LLMResponse, output: TurnOutput) -> None:
        if not response.next_room_id:
            return

        state = self.channel_repo.get_state(channel_id)
        current_room_id = state.current_location_id

        if self.location_repo and not self.location_repo.get_room(response.next_room_id):
            output.debug_notes.append(f"Ignored invalid next_room_id: {response.next_room_id}")
            return

        if self.movement_service and current_room_id:
            if not self.movement_service.validate_next_room(current_room_id, response.next_room_id):
                output.debug_notes.append(
                    f"Ignored non-adjacent next_room_id: {current_room_id} -> {response.next_room_id}"
                )
                return

        self.channel_repo.set_location(channel_id, response.next_room_id)
        output.state_changed = True
        output.next_room_id = response.next_room_id
        self.event_bus.emit(
            GameEvent(
                EventTypes.PLAYER_MOVED,
                {"channel_id": str(channel_id), "from_room": current_room_id, "to_room": response.next_room_id},
            )
        )

    def _apply_required_check(self, channel_id: str, response: LLMResponse, output: TurnOutput) -> None:
        check = (response.required_check or "None").strip()
        if check.lower() == "none" or response.dc <= 0:
            self.channel_repo.clear_active_check(channel_id)
            return
        self.channel_repo.set_active_check(channel_id, check, response.dc)
        output.avrae_commands.append(self._build_check_command(check, response.dc))
        self.event_bus.emit(GameEvent(EventTypes.REQUIRED_CHECK, {"channel_id": str(channel_id), "check": check, "dc": response.dc}))

    def _apply_damage(self, response: LLMResponse, output: TurnOutput) -> None:
        if response.avrae_sync_damage is None:
            return
        amount = max(0, int(response.avrae_sync_damage))
        if amount <= 0:
            return
        output.avrae_commands.append(f"!damage PLAYER {amount}")
        self.event_bus.emit(GameEvent(EventTypes.DAMAGE, {"amount": amount}))

    def _apply_combat_start(self, channel_id: str, response: LLMResponse, output: TurnOutput) -> None:
        combat = getattr(response, "combat_start", None)
        if not combat or not combat.enabled:
            return
        if not combat.monsters:
            output.debug_notes.append("combat_start.enabled=true but monsters list is empty; ignored.")
            return
        if not self.encounter_service:
            output.debug_notes.append("combat_start requested but EncounterService is not configured.")
            return
        state = self.channel_repo.get_state(channel_id)
        encounter_output = self.encounter_service.prepare_room_encounter(
            channel_id=channel_id,
            room_id=state.current_location_id,
            room_data={"monsters": combat.monsters},
            party_level=DEFAULT_PARTY_LEVEL,
            player_count=max(1, len(state.players)),
            scaling_enabled=DEFAULT_ENCOUNTER_SCALING_ENABLED,
            encounter_type=combat.encounter_type,
            xp_reward_total=combat.xp_reward_total,
        )
        output.avrae_commands.extend(encounter_output.avrae_commands)
        output.debug_notes.extend(encounter_output.debug_notes)
        self.event_bus.emit(GameEvent(EventTypes.COMBAT_START, {"channel_id": str(channel_id), "monsters": combat.monsters}))

    def _apply_inventory(self, channel_id: str, player_id: str, response: LLMResponse, output: TurnOutput) -> None:
        if not self.inventory_repo:
            return
        update = response.inventory_update
        if update.gold == 0 and not update.items and not update.ammo:
            return
        current = self.inventory_repo.get_inventory(channel_id, player_id)
        updated = {
            "gold": float(current.get("gold", 0.0)) + float(update.gold),
            "items": self._apply_deltas(current.get("items", {}), update.items),
            "ammo": self._apply_deltas(current.get("ammo", {}), update.ammo),
        }
        self.inventory_repo.save_inventory(channel_id, player_id, updated)
        self.event_bus.emit(GameEvent(EventTypes.INVENTORY_UPDATED, {"channel_id": str(channel_id), "player_id": str(player_id)}))

    def _apply_xp(self, channel_id: str, active_players: List[str], response: LLMResponse, output: TurnOutput) -> None:
        if not self.player_repo or response.xp_reward <= 0:
            return
        xp_each = response.xp_reward // max(1, len(active_players))
        if xp_each <= 0:
            return
        for pid in active_players:
            self.player_repo.add_xp(channel_id, str(pid), xp_each)
        output.debug_notes.append(f"XP kiosztva: {xp_each}/fő")
        self.event_bus.emit(GameEvent(EventTypes.XP_GAINED, {"channel_id": str(channel_id), "xp_each": xp_each}))

    def _apply_rest(self, channel_id: str, response: LLMResponse, output: TurnOutput) -> None:
        rest = response.rest_consequence
        if rest.status == "NONE" or rest.rest_type == "NONE":
            return
        if rest.status == "INTERRUPTED":
            self.event_bus.emit(GameEvent(EventTypes.REST_INTERRUPTED, {"channel_id": str(channel_id), "ambush_monster": rest.ambush_monster}))
            return
        if rest.status == "SUCCESS":
            self.event_bus.emit(GameEvent(EventTypes.REST_COMPLETED, {"channel_id": str(channel_id), "rest_type": rest.rest_type}))

    @staticmethod
    def _apply_deltas(current: Dict[str, Any], deltas: Dict[str, int]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for name, quantity in (current or {}).items():
            try:
                value = int(quantity)
            except (TypeError, ValueError):
                continue
            if value > 0:
                result[str(name)] = value
        for name, delta in (deltas or {}).items():
            new_value = result.get(str(name), 0) + int(delta)
            if new_value > 0:
                result[str(name)] = new_value
            else:
                result.pop(str(name), None)
        return result

    @staticmethod
    def _build_check_command(check: str, dc: int) -> str:
        normalized = check.strip()
        lower = normalized.lower()
        if "save" in lower:
            ability = lower.replace("save", "").strip() or "dex"
            return f"!save {ability} dc {dc}"
        return f"!check {normalized} dc {dc}"
