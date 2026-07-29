"""
LLM/LLM_RESPONSE_PARSER.PY
Robust parser for JSON-only LLM responses, including optional combat_start.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.llm_response import (
    CombatStartRequest,
    InventoryUpdate,
    LLMResponse,
    RestConsequence,
    SecretMessage,
)


class LLMResponseParser:
    @staticmethod
    def parse(text: str) -> LLMResponse:
        cleaned = LLMResponseParser._clean_model_text(text)
        data = LLMResponseParser._parse_json_object(cleaned)
        if data is None:
            return LLMResponse(
                narrative="A jelenet egy pillanatra megakad. Kérlek fogalmazd meg újra rövidebben az akciódat.",
                confidence="low",
                source_usage="fallback",
                needs_clarification=True,
                dm_notes=["LLM response was not valid JSON."],
            )
        return LLMResponseParser._from_dict(data)

    @staticmethod
    def _clean_model_text(text: str) -> str:
        value = (text or "").strip()
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
        return value.strip()

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> LLMResponse:
        inventory_raw = data.get("inventory_update") or {}
        rest_raw = data.get("rest_consequence") or {}
        combat_raw = data.get("combat_start") or {}

        return LLMResponse(
            narrative=str(data.get("narrative") or ""),
            required_check=LLMResponseParser._normalize_check(data.get("required_check")),
            dc=LLMResponseParser._safe_int(data.get("dc"), 0),
            next_room_id=LLMResponseParser._optional_str(data.get("next_room_id")),
            xp_reward=max(0, LLMResponseParser._safe_int(data.get("xp_reward"), 0)),
            milestone_reached=bool(data.get("milestone_reached", False)),
            inventory_update=InventoryUpdate(
                gold=LLMResponseParser._safe_float(inventory_raw.get("gold"), 0.0),
                items=LLMResponseParser._int_dict(inventory_raw.get("items") or {}),
                ammo=LLMResponseParser._int_dict(inventory_raw.get("ammo") or {}),
            ),
            avrae_sync_damage=LLMResponseParser._optional_int(data.get("avrae_sync_damage")),
            secret_messages=LLMResponseParser._secret_messages(data.get("secret_messages") or []),
            rest_consequence=RestConsequence(
                rest_type=str(rest_raw.get("rest_type") or "NONE").upper(),
                status=str(rest_raw.get("status") or "NONE").upper(),
                ambush_monster=LLMResponseParser._optional_str(rest_raw.get("ambush_monster")),
            ),
            combat_start=CombatStartRequest(
                enabled=bool(combat_raw.get("enabled", False)),
                monsters=LLMResponseParser._monster_list(combat_raw.get("monsters") or []),
                xp_reward_total=max(0, LLMResponseParser._safe_int(combat_raw.get("xp_reward_total"), 0)),
                encounter_type=str(combat_raw.get("encounter_type") or "LLM_TRIGGERED"),
                difficulty=str(combat_raw.get("difficulty") or "STANDARD").upper(),
            ),
            confidence=str(data.get("confidence") or "medium"),
            source_usage=str(data.get("source_usage") or "source_based"),
            needs_clarification=bool(data.get("needs_clarification", False)),
            dm_notes=[str(item) for item in (data.get("dm_notes") or []) if item is not None],
        )

    @staticmethod
    def _normalize_check(value: Any) -> str:
        text = str(value or "None").strip()
        return text if text else "None"

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"null", "none"}:
            return None
        return text

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int_dict(value: Dict[str, Any]) -> Dict[str, int]:
        if not isinstance(value, dict):
            return {}
        result: Dict[str, int] = {}
        for key, raw in value.items():
            try:
                amount = int(raw)
            except (TypeError, ValueError):
                continue
            if amount != 0:
                result[str(key)] = amount
        return result

    @staticmethod
    def _secret_messages(value: List[Any]) -> List[SecretMessage]:
        if not isinstance(value, list):
            return []
        result: List[SecretMessage] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            player_id = str(item.get("player_id") or "").strip()
            text = str(item.get("text") or "").strip()
            if player_id and text:
                result.append(SecretMessage(player_id=player_id, text=text))
        return result

    @staticmethod
    def _monster_list(value: List[Any]) -> List[Dict[str, int | str]]:
        if not isinstance(value, list):
            return []
        monsters: List[Dict[str, int | str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("monster_name") or "").strip()
            if not name:
                continue
            count = max(1, LLMResponseParser._safe_int(item.get("count"), 1))
            monsters.append({"name": name, "count": count})
        return monsters
