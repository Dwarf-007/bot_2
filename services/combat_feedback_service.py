"""
SERVICES/COMBAT_FEEDBACK_SERVICE.PY
Processes Avrae bot feedback and emits combat lifecycle events.

C3.7 update:
- Keeps this service as an inbound Avrae feedback adapter.
- Monster-turn advisory output now renders TurnOutput.dm_instructions and
  TurnOutput.suggested_commands instead of reading only legacy avrae_commands.
- No Avrae command dispatch is performed here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from avrae.avrae_parser import AvraeParserService
from core.game_events import EventBus, EventTypes, GameEvent
from core.turn_output import TurnOutput
from models.combat_feedback import CombatFeedbackResult


class CombatFeedbackService:
    def __init__(self, combat_repo, event_bus: EventBus, parser: Optional[AvraeParserService] = None, dm_combat_service=None) -> None:
        self.combat_repo = combat_repo
        self.event_bus = event_bus
        self.parser = parser or AvraeParserService()
        self.combat_repo.ensure_schema()
        self.dm_combat_service = dm_combat_service

    def register_encounter(
        self,
        channel_id: str,
        monsters: List[Dict[str, Any]],
        room_id: Optional[str] = None,
        xp_reward_total: int = 0,
    ) -> None:
        self.combat_repo.start_combat(
            channel_id=str(channel_id),
            room_id=room_id,
            monsters=monsters,
            xp_reward_total=int(xp_reward_total or 0),
        )

    async def process_avrae_message(self, message) -> CombatFeedbackResult:
        channel_id = str(message.channel.id)
        if self.dm_combat_service:
            await self._check_monster_turn(message)
        text = self.parser.extract_full_text(message)
        result = self.process_text(channel_id, text)
        roll_results = self._extract_roll_results(text)
        if roll_results:
            for roll in roll_results:
                payload = {
                    "channel_id": channel_id,
                    "actor": roll.get("actor", ""),
                    "formula": roll.get("formula", ""),
                    "total": roll.get("total"),
                }
                self.event_bus.emit(GameEvent(EventTypes.PLAYER_ROLL, payload))
            result = CombatFeedbackResult(
                combat_started=result.combat_started,
                combat_ended=result.combat_ended,
                defeated_names=result.defeated_names,
                all_monsters_defeated=result.all_monsters_defeated,
                remaining_monsters=result.remaining_monsters,
                roll_results=roll_results,
                raw_text=result.raw_text,
            )
        return result

    def _extract_roll_results(self, text: str) -> List[Dict[str, Any]]:
        return self.parser.extract_roll_results(text)

    async def _check_monster_turn(self, message):
        """If Avrae feedback indicates a monster has the current turn, ask the
        DMCombatService for an advisory TurnOutput and render it safely.

        C3.7 boundary rule:
        - This method may send advisory text to Discord because it is reacting
          to an inbound Discord/Avrae message.
        - It must not dispatch Avrae commands.
        - It must render suggested_commands and dm_instructions, not just the
          legacy avrae_commands field.
        """
        text = self.parser.extract_full_text(message)
        turn_name = self.parser.extract_current_turn_name(text)
        if not turn_name:
            return

        channel_id = str(message.channel.id)
        state = self.dm_combat_service._combats.get(channel_id)
        if not state:
            return

        for uid, mon in state.monsters.items():
            if mon.unique_id == turn_name or mon.name in turn_name:
                output = self.dm_combat_service.execute_monster_turn(channel_id)
                if output:
                    await self._send_turn_output_advisory(message, output)
                break

    async def _send_turn_output_advisory(self, message, output: TurnOutput) -> None:
        """Render a TurnOutput produced by DMCombatService in advisory form.

        This is intentionally a small local formatter to avoid importing the
        DiscordTurnRouter into this service and creating a reverse dependency.
        """
        if output.public_narrative:
            await message.channel.send(output.public_narrative)

        guidance = self._format_dm_guidance(output)
        if guidance:
            await message.channel.send(guidance)

    @staticmethod
    def _format_dm_guidance(output: TurnOutput) -> str:
        parts: List[str] = []

        instructions = [str(item).strip() for item in getattr(output, "dm_instructions", []) or [] if str(item).strip()]
        if instructions:
            parts.append("**DM instrukció**\n" + "\n".join(f"- {item}" for item in instructions))

        if hasattr(output, "all_suggested_commands"):
            commands = output.all_suggested_commands()
        else:
            commands = [str(command).strip() for command in getattr(output, "suggested_commands", []) or [] if str(command).strip()]
            legacy = [str(command).strip() for command in getattr(output, "avrae_commands", []) or [] if str(command).strip()]
            for command in legacy:
                if command not in commands:
                    commands.append(command)

        if commands:
            command_block = "\n".join(commands)
            parts.append(
                "**Javasolt DM / Avrae parancsok**\n"
                "```text\n"
                f"{command_block}\n"
                "```\n"
                "_Az AI-DM nem hajtja végre automatikusan ezeket a parancsokat._"
            )

        return "\n".join(parts)

    def process_text(self, channel_id: str, text: str) -> CombatFeedbackResult:
        defeated = self.parser.extract_defeated_names(text)
        if not defeated:
            snapshot = self.combat_repo.get_combat_state(channel_id)
            return CombatFeedbackResult(
                defeated_names=[],
                all_monsters_defeated=False,
                remaining_monsters=snapshot.monsters,
                raw_text=text,
            )

        matched: List[str] = []
        for name in defeated:
            if self.combat_repo.register_defeated_monster(channel_id, name):
                matched.append(name)

        snapshot = self.combat_repo.get_combat_state(channel_id)
        all_dead = bool(matched) and not snapshot.active

        if all_dead:
            self.event_bus.emit(
                GameEvent(
                    EventTypes.ALL_MONSTERS_DEFEATED,
                    {
                        "channel_id": str(channel_id),
                        "room_id": snapshot.room_id,
                        "xp_reward_total": snapshot.xp_reward_total,
                        "defeated_names": matched,
                    },
                )
            )
            self.event_bus.emit(
                GameEvent(
                    EventTypes.COMBAT_END,
                    {
                        "channel_id": str(channel_id),
                        "room_id": snapshot.room_id,
                    },
                )
            )
            self.combat_repo.clear_combat(channel_id)

        return CombatFeedbackResult(
            combat_ended=all_dead,
            defeated_names=matched,
            all_monsters_defeated=all_dead,
            remaining_monsters=snapshot.monsters,
            raw_text=text,
        )
