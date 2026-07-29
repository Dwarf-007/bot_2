"""
SERVICES/COMBAT_RECOMMENDATION_BUILDER.PY
Builds DM-facing TurnOutput recommendations for AI-DM combat.

Patch purpose:
- Make advisory commands visible in the narrative/instructions, not only hidden in
  TurnOutput.suggested_commands.
- Clearly distinguish DM commands from player commands.
- Keep the system advisory-only: no Avrae auto-dispatch.

Boundary:
- No Discord I/O.
- No Avrae dispatch.
- No LLM calls.
- No combat session lifecycle mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.turn_output import TurnOutput
from services.combat_session_service import CombatState, MonsterState, MonsterTurnCompletion
from services.monster_decision_service import MonsterActionDecision


@dataclass(frozen=True)
class MonsterTurnAdvisoryInput:
    """Data needed to render a monster-turn recommendation."""

    monster: MonsterState
    target_id: Optional[str]
    action: Dict[str, Any]
    attack_bonus: int
    hit: bool
    damage: int
    decision: MonsterActionDecision
    completion: MonsterTurnCompletion = field(default_factory=MonsterTurnCompletion)


class CombatRecommendationBuilder:
    """Builds TurnOutput objects for combat advisory flow."""

    def build_start_combat_output(self, state: CombatState) -> TurnOutput:
        suggested_commands = self.build_start_combat_suggested_commands(state)
        narrative = self.build_start_combat_narrative(state, suggested_commands)

        return TurnOutput(
            public_narrative=narrative,
            dm_instructions=[
                "Az AI-DM nem küldi el automatikusan az Avrae parancsokat.",
                "A DM manuálisan adja ki a DM parancsokat, a játékosok pedig a player parancsot.",
                "Ha Avrae-t használtok, az alábbi parancslista a javasolt indítási sorrend.",
            ],
            suggested_commands=suggested_commands,
        )

    def build_start_combat_narrative(self, state: CombatState, suggested_commands: Optional[List[str]] = None) -> str:
        commands = suggested_commands or self.build_start_combat_suggested_commands(state)
        dm_commands = [command for command in commands if command != "!init join"]
        player_commands = [command for command in commands if command == "!init join"]

        lines = [
            f"⚔️ **Harc kezdődik!** {len(state.monsters)} szörny tűnik fel.",
            "",
            "**Javasolt Avrae parancsok, manuális végrehajtással:**",
            "",
            "**DM adja ki:**",
        ]
        lines.extend(f"- `{command}`" for command in dm_commands)
        lines.append("")
        lines.append("**Játékosok adják ki:**")
        if player_commands:
            lines.extend(f"- `{command}`" for command in player_commands)
        else:
            lines.append("- `!init join`")
        lines.append("")
        lines.append("Az AI-DM csak javasolja ezeket, nem hajtja végre automatikusan.")
        return "\n".join(lines)

    def build_start_combat_suggested_commands(self, state: CombatState) -> List[str]:
        commands = ["!init begin"]
        for monster in state.monsters.values():
            commands.append(f"!init add 1 {monster.name} -hp {monster.current_hp}")
        commands.append("!init join")
        return commands

    def build_monster_turn_output(self, data: MonsterTurnAdvisoryInput) -> TurnOutput:
        suggested_commands = self.build_monster_turn_suggested_commands(data)
        narrative = self.build_monster_turn_narrative(data, suggested_commands)

        debug_notes = []
        if data.decision.source:
            debug_notes.append(f"Monster decision source: {data.decision.source}")
        if data.decision.reason:
            debug_notes.append(f"Monster decision reason: {data.decision.reason}")
        debug_notes.extend(data.decision.debug_notes)

        return TurnOutput(
            public_narrative=narrative,
            dm_instructions=[
                "A következő parancsok csak javaslatok. A DM döntse el, hogy Avrae-ban kiadja-e őket.",
                "Az AI-DM nem hajt végre automatikus Avrae parancsot.",
            ],
            suggested_commands=suggested_commands,
            debug_notes=debug_notes,
        )

    def build_monster_turn_narrative(self, data: MonsterTurnAdvisoryInput, suggested_commands: Optional[List[str]] = None) -> str:
        lines = [self.build_attack_narrative(
            monster=data.monster,
            target_id=data.target_id,
            hit=data.hit,
            damage=data.damage,
        )]

        if data.completion.removed_monster_id:
            lines.append(f"💀 {data.completion.removed_monster_id} elpusztult!")

        if data.completion.all_monsters_defeated:
            lines.append("🎉 Minden szörny legyőzve! A harc véget ért.")
            if data.completion.total_xp > 0:
                lines.append(f"Szerezett XP: {data.completion.total_xp}")

        commands = suggested_commands or self.build_monster_turn_suggested_commands(data)
        if commands:
            lines.append("")
            lines.append("**Javasolt DM / Avrae parancsok, manuális végrehajtással:**")
            lines.extend(f"- `{command}`" if not command.startswith("#") else f"- {command}" for command in commands)
            lines.append("Az AI-DM csak javasolja ezeket, nem hajtja végre automatikusan.")

        return "\n".join(lines)

    def build_monster_turn_suggested_commands(self, data: MonsterTurnAdvisoryInput) -> List[str]:
        commands = [f"!r 1d20+{data.attack_bonus} # {data.monster.unique_id} attack"]
        if data.hit and data.damage > 0 and data.target_id:
            commands.append(
                f"# Javaslat: alkalmazd Avrae-ban a {data.damage} sebzést <@{data.target_id}> célponton, ha ez a DM döntése szerint érvényes."
            )
        return commands

    @staticmethod
    def build_attack_narrative(monster: MonsterState, target_id: Optional[str], hit: bool, damage: int) -> str:
        target_name = f"<@{target_id}>" if target_id else "egy játékosra"
        if hit:
            return f"{monster.unique_id} megtámadja {target_name}-t: **találat** {damage} sebzéssel!"
        return f"{monster.unique_id} megtámadja {target_name}-t, de **nem talál**."
