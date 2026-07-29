"""
SERVICES/MONSTER_DECISION_SERVICE.PY
Monster action decision helper for AI-DM combat.

C4.2 extraction:
- Owns monster action selection.
- Owns target selection fallback.
- Owns LLM combat-decision prompt construction and parsing.

Boundary:
- No Discord I/O.
- No Avrae dispatch.
- No TurnOutput construction.
- No combat session lifecycle mutation.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from services.combat_session_service import CombatState, MonsterState


@dataclass(frozen=True)
class MonsterActionDecision:
    """Decision returned by MonsterDecisionService."""

    action: Dict[str, Any]
    target_id: Optional[str]
    source: str = "fallback"
    reason: str = ""
    raw_response: Any = None
    debug_notes: list[str] = field(default_factory=list)


class MonsterDecisionService:
    """Selects a monster action and target without mutating combat state."""

    def __init__(self, llm_adapter=None) -> None:
        self.llm_adapter = llm_adapter

    def choose_action(self, state: CombatState, monster: MonsterState) -> MonsterActionDecision:
        """
        Choose an action and a target for a monster.

        The service first tries the configured LLM adapter. If no adapter is
        available or parsing fails, it returns a deterministic fallback action
        using the monster's basic attack profile and a random known player.
        """
        fallback = self._fallback_decision(state, monster)
        if self.llm_adapter is None:
            return fallback

        prompt = self._build_prompt(state, monster)
        try:
            response = self.llm_adapter.generate(prompt)
            data = json.loads(response) if isinstance(response, str) else response
            if not isinstance(data, dict):
                return MonsterActionDecision(
                    action=fallback.action,
                    target_id=fallback.target_id,
                    source="fallback",
                    reason="LLM response was not a JSON object.",
                    raw_response=response,
                    debug_notes=["invalid_llm_response_type"],
                )

            action_index = int(data.get("action_index", 0) or 0)
            if monster.actions and 0 <= action_index < len(monster.actions):
                action = monster.actions[action_index]
            else:
                action = fallback.action

            target_id = data.get("target_id") or fallback.target_id
            reason = str(data.get("reason") or "").strip()
            return MonsterActionDecision(
                action=action,
                target_id=target_id,
                source="llm",
                reason=reason,
                raw_response=data,
            )
        except Exception as exc:
            return MonsterActionDecision(
                action=fallback.action,
                target_id=fallback.target_id,
                source="fallback",
                reason="LLM decision failed; fallback action selected.",
                raw_response=repr(exc),
                debug_notes=["llm_decision_failed"],
            )

    def choose_random_player(self, state: CombatState) -> Optional[str]:
        """Return a random known player id, or None when no player AC is known."""
        if state.player_ac:
            return random.choice(list(state.player_ac.keys()))
        return None

    def _fallback_decision(self, state: CombatState, monster: MonsterState) -> MonsterActionDecision:
        return MonsterActionDecision(
            action=self._basic_attack(monster),
            target_id=self.choose_random_player(state),
            source="fallback",
            reason="basic_attack_fallback",
        )

    @staticmethod
    def _basic_attack(monster: MonsterState) -> Dict[str, Any]:
        return {
            "type": "melee",
            "name": "basic attack",
            "bonus": monster.attack_bonus,
            "damage": monster.damage_dice,
        }

    def _build_prompt(self, state: CombatState, monster: MonsterState) -> str:
        possible_targets = list(state.player_ac.keys()) if state.player_ac else ["unknown"]
        actions_desc = "\n".join(
            f"- {a.get('name', 'attack')}: bonus {a.get('bonus')}, damage {a.get('damage')}"
            for a in monster.actions
        ) if monster.actions else "basic melee attack"

        return (
            f"Te vagy a DM egy D&D 5e játékban. Egy szörny ({monster.name}) következik a körben.\n"
            f"Statisztikák: AC {monster.ac}, HP {monster.current_hp}/{monster.max_hp}, "
            f"támadás bónusz: {monster.attack_bonus}, sebzés: {monster.damage_dice}\n"
            f"Lehetséges akciók:\n{actions_desc}\n"
            f"Lehetséges célpontok (játékos ID-k): {', '.join(possible_targets)}\n"
            "Válassz egy akciót és egy célpontot. Válaszolj JSON formátumban:\n"
            '{"action_index": 0, "target_id": "player_id", "reason": "röviden"}'
        )
