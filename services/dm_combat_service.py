# services/dm_combat_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.turn_output import TurnOutput
from services.bestiary_service import BestiaryService
from services.combat_dice_service import CombatDiceService
from services.combat_recommendation_builder import CombatRecommendationBuilder, MonsterTurnAdvisoryInput
from services.combat_session_service import CombatSessionService, CombatState, MonsterState
from services.monster_decision_service import MonsterDecisionService


class DMCombatService:
    """
    Compatibility facade for DM-driven monster combat assistance.

    C4.1 decomposition:
    - Combat helper-state lifecycle moved to CombatSessionService.

    C4.2 decomposition:
    - Monster action and target selection moved to MonsterDecisionService.

    C4.3 decomposition:
    - Combat TurnOutput/narrative/suggested-command construction moved to
      CombatRecommendationBuilder.

    C4.4 final facade cleanup:
    - Local advisory dice helpers moved to CombatDiceService.
    - DMCombatService is now primarily orchestration and compatibility facade.

    C3/C4 boundary rule:
    - No automatic Avrae dispatch.
    - Suggested commands are DM-facing advisory output.
    - Avrae remains authoritative for initiative, HP, attacks, damage, spells,
      and conditions when the table uses Avrae.
    """

    def __init__(
        self,
        llm_adapter,
        bestiary_service: BestiaryService | None = None,
        avrae_dispatcher=None,
        bestiary_path: str = "data/bestiary.json",
        player_manager=None,
        session_service: CombatSessionService | None = None,
        decision_service: MonsterDecisionService | None = None,
        recommendation_builder: CombatRecommendationBuilder | None = None,
        dice_service: CombatDiceService | None = None,
    ) -> None:
        self.llm_adapter = llm_adapter
        self.bestiary_service = bestiary_service or BestiaryService(bestiary_path)
        self.player_manager = player_manager
        # Kept only for constructor compatibility during C3/C4 migration.
        # Do not call this dispatcher from canonical combat flow.
        self.avrae_dispatcher = avrae_dispatcher
        self.session_service = session_service or CombatSessionService(
            bestiary_service=self.bestiary_service,
            bestiary_path=bestiary_path,
        )
        self.decision_service = decision_service or MonsterDecisionService(llm_adapter=llm_adapter)
        self.recommendation_builder = recommendation_builder or CombatRecommendationBuilder()
        self.dice_service = dice_service or CombatDiceService()
        # Backward compatibility: CombatFeedbackService currently inspects this.
        self._combats = self.session_service.combats

    def get_monster_stats(self, name: str) -> Optional[Dict[str, Any]]:
        return self.session_service.get_monster_stats(name)

    def start_combat(
        self,
        channel_id: str,
        monsters_data: List[Dict[str, Any]],
        player_ids: List[str] = None,
    ) -> TurnOutput:
        result = self.session_service.start_combat_session(
            channel_id=str(channel_id),
            monsters_data=monsters_data,
        )
        if not result.ok:
            if result.reason == "active_combat_exists":
                return TurnOutput(public_narrative="Már folyamatban van egy harc ezen a csatornán.")
            return TurnOutput(public_narrative="Nincsenek érvényes szörnyek a harchoz.")

        state = result.state
        assert state is not None
        return self.recommendation_builder.build_start_combat_output(state)

    def execute_monster_turn(self, channel_id: str) -> Optional[TurnOutput]:
        current = self.session_service.get_current_monster_for_turn(str(channel_id))
        if not current:
            return None

        uid, monster = current
        state = self.session_service.get_combat_state(str(channel_id))
        if not state:
            return None

        decision = self.decision_service.choose_action(state, monster)
        action = decision.action
        target_id = decision.target_id

        target_ac = state.player_ac.get(target_id, 12)
        attack_bonus = int(action.get("bonus", monster.attack_bonus) or monster.attack_bonus)
        attack_roll = self.dice_service.roll_d20_plus(attack_bonus)
        hit = attack_roll >= target_ac

        damage = 0
        if hit:
            damage = self.dice_service.roll_damage(action.get("damage", monster.damage_dice))

        if hit and action.get("self_damage"):
            monster.current_hp -= int(action["self_damage"])

        completion = self.session_service.complete_monster_turn(str(channel_id), uid)
        advisory = MonsterTurnAdvisoryInput(
            monster=monster,
            target_id=target_id,
            action=action,
            attack_bonus=attack_bonus,
            hit=hit,
            damage=damage,
            decision=decision,
            completion=completion,
        )
        return self.recommendation_builder.build_monster_turn_output(advisory)

    # ------------------------------------------------------------------
    # Compatibility wrappers kept for callers/tests during C4 migration.
    # ------------------------------------------------------------------
    def _get_monster_action(self, channel_id: str, monster: MonsterState) -> Tuple[Optional[Dict], Optional[str]]:
        state = self.session_service.get_combat_state(channel_id)
        if not state:
            return None, None
        decision = self.decision_service.choose_action(state, monster)
        return decision.action, decision.target_id

    def _choose_random_player(self, state: CombatState) -> Optional[str]:
        return self.decision_service.choose_random_player(state)

    def _roll_damage(self, damage_str: str) -> int:
        """Compatibility wrapper. Prefer CombatDiceService.roll_damage()."""
        return self.dice_service.roll_damage(damage_str)

    def _build_attack_narrative(self, monster: MonsterState, target_id: str, hit: bool, damage: int) -> str:
        return self.recommendation_builder.build_attack_narrative(monster, target_id, hit, damage)

    def set_player_ac(self, channel_id: str, player_id: str, ac: int) -> None:
        self.session_service.set_player_ac(channel_id, player_id, ac)

    def on_player_roll(self, event) -> None:
        channel_id = str(event.payload.get("channel_id", ""))
        actor = str(event.payload.get("actor", "")).strip()
        formula = str(event.payload.get("formula", "")).strip()
        total = event.payload.get("total")
        self.session_service.append_player_roll(channel_id, actor, formula, total)

    def is_active(self, channel_id: str) -> bool:
        return self.session_service.is_active(channel_id)

    def get_combat_state(self, channel_id: str) -> Optional[CombatState]:
        return self.session_service.get_combat_state(channel_id)
