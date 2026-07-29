"""
SERVICES/COMBAT_RUNTIME_SMOKE_SERVICE.PY
Deterministic, dependency-light smoke runner for the refactored Combat Runtime.

C5.1 purpose:
- Prove the C3/C4 advisory Combat Runtime green path works without Discord.
- Prove the smoke does not need Avrae or Avrae auto-dispatch.
- Exercise DMCombatService facade plus extracted C4 components:
  - CombatSessionService
  - MonsterDecisionService
  - CombatRecommendationBuilder
  - CombatDiceService

Boundary:
- No Discord I/O.
- No Avrae dispatch.
- No database dependency.
- Uses fake LLM, fake bestiary, deterministic dice.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from services.dm_combat_service import DMCombatService


@dataclass(frozen=True)
class CombatRuntimeSmokeStep:
    name: str
    ok: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CombatRuntimeSmokeResult:
    ok: bool
    steps: List[CombatRuntimeSmokeStep] = field(default_factory=list)
    public_narratives: List[str] = field(default_factory=list)
    suggested_commands: List[str] = field(default_factory=list)
    debug_notes: List[str] = field(default_factory=list)
    active_after_start: bool = False
    active_after_turn: bool = False
    no_legacy_avrae_commands: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "steps": [step.to_dict() for step in self.steps],
            "public_narratives": list(self.public_narratives),
            "suggested_commands": list(self.suggested_commands),
            "debug_notes": list(self.debug_notes),
            "active_after_start": self.active_after_start,
            "active_after_turn": self.active_after_turn,
            "no_legacy_avrae_commands": self.no_legacy_avrae_commands,
        }

    def summary_text(self) -> str:
        passed = sum(1 for step in self.steps if step.ok)
        lines = [f"Combat Runtime smoke: {passed}/{len(self.steps)} passed"]
        for step in self.steps:
            prefix = "OK" if step.ok else "FAIL"
            line = f"- {prefix} {step.name}: {step.message}"
            lines.append(line.rstrip())
        return "
".join(lines)


class _SmokeLLM:
    def generate(self, prompt: str) -> str:
        return '{"action_index": 0, "target_id": "p1", "reason": "smoke target"}'


class _SmokeBestiary:
    def get_monster_stats(self, name: str) -> Dict[str, Any]:
        return {
            "hp": {"average": 7},
            "ac": [13],
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
            "action": [
                {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2"}
            ],
        }


class _SmokeDice:
    def roll_d20_plus(self, bonus: int = 0) -> int:
        return 20 + int(bonus or 0)

    def roll_damage(self, damage_str: str) -> int:
        return 6


class _ForbiddenDispatcher:
    """Fails loudly if any refactored component tries to auto-dispatch Avrae."""

    def __init__(self) -> None:
        self.called = False

    def is_available(self) -> bool:
        self.called = True
        raise AssertionError("Combat smoke must not call avrae_dispatcher.is_available()")

    def dispatch_commands(self, commands):
        self.called = True
        raise AssertionError("Combat smoke must not call avrae_dispatcher.dispatch_commands(...)")


class CombatRuntimeSmokeService:
    """Runs a deterministic green-path smoke against the combat facade."""

    def __init__(self, dm_combat_service: Optional[DMCombatService] = None) -> None:
        self.dispatcher = _ForbiddenDispatcher()
        self.dm_combat_service = dm_combat_service or DMCombatService(
            llm_adapter=_SmokeLLM(),
            bestiary_service=_SmokeBestiary(),
            avrae_dispatcher=self.dispatcher,
            dice_service=_SmokeDice(),
        )

    def run(self, channel_id: str = "combat-smoke-channel") -> CombatRuntimeSmokeResult:
        steps: List[CombatRuntimeSmokeStep] = []
        narratives: List[str] = []
        commands: List[str] = []
        debug_notes: List[str] = []
        no_legacy_avrae_commands = True

        start_output = self.dm_combat_service.start_combat(
            channel_id=channel_id,
            monsters_data=[{"name": "Goblin", "count": 1}],
        )
        narratives.append(start_output.public_narrative)
        commands.extend(start_output.suggested_commands)
        debug_notes.extend(start_output.debug_notes)
        no_legacy_avrae_commands = no_legacy_avrae_commands and not bool(start_output.avrae_commands)
        active_after_start = self.dm_combat_service.is_active(channel_id)

        steps.append(CombatRuntimeSmokeStep(
            name="start_combat_public_narrative",
            ok=bool(start_output.public_narrative.strip()),
            message="Combat start produced public narrative.",
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="start_combat_suggested_commands",
            ok="!init begin" in start_output.suggested_commands and any("Goblin" in item for item in start_output.suggested_commands),
            message="Combat start produced DM-facing suggested commands.",
            details={"commands": list(start_output.suggested_commands)},
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="start_combat_no_legacy_avrae_commands",
            ok=not bool(start_output.avrae_commands),
            message="Combat start did not use legacy avrae_commands output.",
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="start_combat_state_active",
            ok=active_after_start,
            message="Combat helper state is active after start.",
        ))

        self.dm_combat_service.set_player_ac(channel_id, "p1", 12)
        turn_output = self.dm_combat_service.execute_monster_turn(channel_id)
        if turn_output:
            narratives.append(turn_output.public_narrative)
            commands.extend(turn_output.suggested_commands)
            debug_notes.extend(turn_output.debug_notes)
            no_legacy_avrae_commands = no_legacy_avrae_commands and not bool(turn_output.avrae_commands)

        active_after_turn = self.dm_combat_service.is_active(channel_id)
        steps.append(CombatRuntimeSmokeStep(
            name="monster_turn_output_exists",
            ok=turn_output is not None,
            message="Monster turn produced TurnOutput.",
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="monster_turn_public_narrative",
            ok=bool(turn_output and turn_output.public_narrative.strip()),
            message="Monster turn produced public narrative.",
        ))
        turn_commands = turn_output.suggested_commands if turn_output else []
        steps.append(CombatRuntimeSmokeStep(
            name="monster_turn_suggested_roll_command",
            ok=any(command.startswith("!r 1d20+") for command in turn_commands),
            message="Monster turn produced advisory roll command.",
            details={"commands": list(turn_commands)},
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="monster_turn_no_legacy_avrae_commands",
            ok=not bool(turn_output and turn_output.avrae_commands),
            message="Monster turn did not use legacy avrae_commands output.",
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="monster_decision_debug_notes",
            ok=any("Monster decision source" in note for note in debug_notes),
            message="Monster decision debug notes were propagated.",
            details={"debug_notes": list(debug_notes)},
        ))
        steps.append(CombatRuntimeSmokeStep(
            name="no_avrae_dispatcher_called",
            ok=not self.dispatcher.called,
            message="Avrae dispatcher was not called during smoke.",
        ))

        ok = all(step.ok for step in steps)
        return CombatRuntimeSmokeResult(
            ok=ok,
            steps=steps,
            public_narratives=narratives,
            suggested_commands=commands,
            debug_notes=debug_notes,
            active_after_start=active_after_start,
            active_after_turn=active_after_turn,
            no_legacy_avrae_commands=no_legacy_avrae_commands,
        )
