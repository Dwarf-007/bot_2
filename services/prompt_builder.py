"""
SERVICES/PROMPT_BUILDER.PY
Builds deterministic, JSON-only prompts for the AI Dungeon Master.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class PromptBuilder:
    JSON_CONTRACT = {
        "narrative": "A játékosoknak szánt végső, tiszta narráció magyarul.",
        "required_check": "Perception | Investigation | Stealth | Dexterity Save | Strength | None",
        "dc": 0,
        "next_room_id": None,
        "xp_reward": 0,
        "milestone_reached": False,
        "inventory_update": {"gold": 0.0, "items": {}, "ammo": {}},
        "avrae_sync_damage": None,
        "secret_messages": [{"player_id": "123456789", "text": "Titkos információ csak neki."}],
        "rest_consequence": {"rest_type": "SHORT | LONG | NONE", "status": "SUCCESS | INTERRUPTED | NONE", "ambush_monster": None},
        "combat_start": {
            "enabled": False,
            "monsters": [{"name": "Goblin", "count": 2}],
            "xp_reward_total": 0,
            "encounter_type": "LLM_TRIGGERED | STATIC_ROOM | TRAP | REST_AMBUSH",
            "difficulty": "EASY | STANDARD | HARD | DEADLY",
        },
        "confidence": "high | medium | low",
        "source_usage": "source_based | inferred | freeplay | fallback",
        "needs_clarification": False,
        "dm_notes": [],
    }

    def build(self, turn_context: Dict[str, Any], player_action: str) -> str:
        mode = str(turn_context.get("mode") or "campaign").lower()
        payload = {
            "mode": mode,
            "style": turn_context.get("style", "grimdark"),
            "difficulty": turn_context.get("difficulty", "standard"),
            "game_state": turn_context.get("current_state", "EXPLORATION"),
            "active_player": turn_context.get("player") or turn_context.get("active_player"),
            "current_location_id": turn_context.get("current_location_id"),
            "room_facts": turn_context.get("room_facts", ""),
            "room_exits": turn_context.get("room_exits", {}),
            "summary_text": turn_context.get("summary_text", ""),
            "messages": self._trim_messages(turn_context.get("messages", [])),
            "rag_chunks": turn_context.get("rag_chunks", []),
            "player_action": player_action,
        }
        return f"""
Te egy AI Dungeon Master vagy D&D 5e stílusú játékhoz.
A játék nyelve magyar.

ALAPSZABÁLYOK:
- Mindig kizárólag egyetlen valid JSON objektummal válaszolj.
- Ne használj markdown kódblokkot.
- Ne írj magyarázatot a JSON elé vagy mögé.
- Ne dönts a játékos karaktere helyett.
- Ne kezeld közvetlenül a HP-t, initiative-et vagy combat mechanikát; ezeket Avrae kezeli.
- Ha mechanikai dobás kell, a required_check és dc mezőkben jelezd.
- Ha sebzést kell Avrae felé szinkronizálni, az avrae_sync_damage mezőt használd.
- Ha harc kezdődik, a combat_start.enabled=true és add meg a monsters listát.
- A secret_messages tartalma nem kerülhet bele a narrative mezőbe.

MÓDSPECIFIKUS SZABÁLYOK:
{self._mode_rules(mode)}

KÖTELEZŐ JSON SÉMA:
{json.dumps(self.JSON_CONTRACT, ensure_ascii=False, indent=2)}

JÁTÉK KONTEKSTUS:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Válaszolj most kizárólag a fenti sémának megfelelő JSON objektummal.
""".strip()

    @staticmethod
    def _mode_rules(mode: str) -> str:
        if mode == "campaign":
            return (
                "- Campaign módban a room_facts és RAG adatok elsődlegesek.\n"
                "- Ne találj ki kampánykritikus tényeket, NPC-ket, lootot vagy kijáratot, ha nincs rá forrás.\n"
                "- Combatot csak akkor indíts, ha room_facts/RAG vagy determinisztikus esemény indokolja.\n"
                "- Ha a forrás nem elég, needs_clarification=true és confidence=low."
            )
        return (
            "- Freeplay módban kreatívan generálhatsz világot és helyzeteket.\n"
            "- A generált fontos tények legyenek később persistálhatóak.\n"
            "- Ne írj felül meglévő state-et ellentmondásosan."
        )

    @staticmethod
    def _trim_messages(messages: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        if not isinstance(messages, list):
            return []
        return messages[-limit:]
