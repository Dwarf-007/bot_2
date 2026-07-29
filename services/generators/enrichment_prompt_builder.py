"""
SERVICES/GENERATORS/ENRICHMENT_PROMPT_BUILDER.PY

Builds strict prompts for optional LLM-based enrichment.
Sprint 3 still has a deterministic fallback and does not require an LLM.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class EnrichmentPromptBuilder:
    def build_campaign_prompt(self, bundle_summary: Dict[str, Any], theme: str, tone: str) -> str:
        schema = {
            "premise": "short campaign premise",
            "factions": [
                {"faction_id": "slug", "name": "name", "agenda": "agenda", "attitude": "hostile|neutral|friendly", "rooms": ["room_id"]}
            ],
            "quests": [
                {"quest_id": "slug", "title": "title", "hook": "hook", "objective": "objective", "reward_hint": "reward", "related_rooms": ["room_id"]}
            ],
            "secrets": ["secret"],
            "rumors": ["rumor"],
        }
        return (
            "You are enriching a procedurally generated dungeon for a tabletop RPG.\n"
            "Do not contradict the provided room graph. Do not invent rooms.\n"
            "Return STRICT JSON only, matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"Theme: {theme}\nTone: {tone}\n"
            f"Bundle summary:\n{json.dumps(bundle_summary, ensure_ascii=False, indent=2)}\n"
        )

    def build_room_prompt(self, room: Dict[str, Any], theme: str, tone: str) -> str:
        schema = {
            "boxed_text": "2-4 sentence read-aloud text",
            "gm_notes": ["note"],
            "clues": ["clue"],
            "complications": ["complication"],
        }
        compact_room = {
            "room_id": room.get("room_id"),
            "title": room.get("title"),
            "facts": room.get("facts"),
            "exits": room.get("exits"),
            "traps": room.get("traps", []),
            "monsters": room.get("monsters", []),
        }
        return (
            "Enrich this dungeon room for a tabletop RPG.\n"
            "Preserve all factual exits, traps and monsters. Do not invent new exits.\n"
            "Return STRICT JSON only, matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"Theme: {theme}\nTone: {tone}\n"
            f"Room:\n{json.dumps(compact_room, ensure_ascii=False, indent=2)}\n"
        )
