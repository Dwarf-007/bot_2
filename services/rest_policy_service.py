"""
SERVICES/REST_POLICY_SERVICE.PY
Pure deterministic rest policy evaluation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.rest_models import RestPolicy, RestResolution


class RestPolicyService:
    def resolve_rest(self, rest_type: str, room_data: Dict[str, Any], policy: RestPolicy | None = None) -> RestResolution:
        policy = policy or RestPolicy()
        normalized_type = str(rest_type or "NONE").upper()

        if normalized_type == "SHORT" and not policy.allow_short_rest:
            return RestResolution(rest_type="SHORT", status="DENIED", reason="short_rest_not_allowed")
        if normalized_type == "LONG" and not policy.allow_long_rest:
            return RestResolution(rest_type="LONG", status="DENIED", reason="long_rest_not_allowed")
        if normalized_type not in {"SHORT", "LONG"}:
            return RestResolution(rest_type="NONE", status="NONE", reason="no_rest_requested")

        if policy.interrupt_on_dangerous_room and self._is_dangerous_room(room_data):
            monsters = self._ambush_monsters(room_data, policy)
            return RestResolution(
                rest_type=normalized_type,
                status="INTERRUPTED",
                reason="dangerous_room_ambush",
                ambush_monsters=monsters,
                xp_reward_total=policy.default_ambush_xp,
            )

        return RestResolution(rest_type=normalized_type, status="SUCCESS", reason="safe_rest")

    @staticmethod
    def _is_dangerous_room(room_data: Dict[str, Any]) -> bool:
        if not room_data:
            return False
        raw = room_data.get("raw") or {}
        flags = room_data.get("flags") or raw.get("flags") or []
        if isinstance(flags, list) and any(str(flag).lower() in {"danger", "dangerous", "unsafe", "no_rest"} for flag in flags):
            return True

        facts = str(room_data.get("facts") or "").lower()
        danger_words = ["danger", "dangerous", "unsafe", "wandering monster", "ambush", "csapda", "veszély", "rajtaütés"]
        if any(word in facts for word in danger_words):
            return True

        monsters = room_data.get("monsters") or []
        return bool(monsters)

    @staticmethod
    def _ambush_monsters(room_data: Dict[str, Any], policy: RestPolicy) -> List[Dict[str, int | str]]:
        monsters = room_data.get("monsters") or []
        result: List[Dict[str, int | str]] = []
        if isinstance(monsters, list):
            for monster in monsters[:2]:
                if not isinstance(monster, dict):
                    continue
                name = str(monster.get("name") or monster.get("monster_name") or "").strip()
                if not name:
                    continue
                try:
                    count = int(monster.get("count", 1))
                except (TypeError, ValueError):
                    count = 1
                result.append({"name": name, "count": max(1, count)})
        if result:
            return result
        if policy.default_ambush_monster:
            return [{"name": policy.default_ambush_monster, "count": 1}]
        return []
