"""
SERVICES/TRAP_FAILURE_CONSEQUENCE_ENGINE.PY
Deterministic trap evaluation on failed movement / failed interaction.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from core.trap_consequence_models import (
    TrapDefinition,
    TrapEvaluationBundle,
    TrapTriggerContext,
    TrapTriggerResult,
)
from services.trap_definition_parser import TrapDefinitionParser


class TrapFailureConsequenceEngine:
    def __init__(self, parser: Optional[TrapDefinitionParser] = None) -> None:
        self.parser = parser or TrapDefinitionParser()

    def evaluate_exit_failure_traps_stateful(
        self,
        room_data: Dict[str, Any],
        context: TrapTriggerContext,
        trap_state: Dict[str, Any],
    ) -> TrapEvaluationBundle:
        return self.evaluate(
            room_data=room_data,
            context=context,
            trap_state=trap_state,
            trigger_key="exit_failure",
        )

    def evaluate(
        self,
        room_data: Dict[str, Any],
        context: TrapTriggerContext,
        trap_state: Dict[str, Any],
        trigger_key: str,
    ) -> TrapEvaluationBundle:
        traps = self.parser.parse_room_traps(room_data)
        updated_state = deepcopy(trap_state or {})
        room_state = updated_state.setdefault(context.room_id, {})
        triggered: List[TrapTriggerResult] = []
        debug_notes: List[str] = []

        for trap in traps:
            if not self._matches_trigger(trap, trigger_key, context):
                continue
            existing = room_state.get(trap.name, {})
            if trap.once and existing.get("triggered"):
                debug_notes.append(f"Trap skipped because already triggered: {trap.name}")
                continue

            result = TrapTriggerResult(
                trap_name=trap.name,
                triggered=True,
                damage=max(0, int(trap.damage or 0)),
                damage_type=trap.damage_type,
                required_check=trap.required_check,
                dc=max(0, int(trap.dc or 0)),
                effect_tags=list(trap.effect_tags),
                narrative_hint=trap.description or f"Csapda aktiválódik: {trap.name}",
            )
            triggered.append(result)
            room_state[trap.name] = {
                "triggered": True,
                "disarmed": False,
                "last_trigger": trigger_key,
            }

        return TrapEvaluationBundle(
            room_id=context.room_id,
            triggered_results=triggered,
            updated_trap_state=updated_state,
            debug_notes=debug_notes,
        )

    @staticmethod
    def _matches_trigger(trap: TrapDefinition, trigger_key: str, context: TrapTriggerContext) -> bool:
        triggers = {str(value).lower() for value in trap.trigger_on}
        if trigger_key.lower() in triggers:
            return True
        if "any" in triggers:
            return True
        if context.failure_reason and context.failure_reason.lower() in triggers:
            return True
        return False
