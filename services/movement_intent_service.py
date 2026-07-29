"""
SERVICES/MOVEMENT_INTENT_SERVICE.PY
Deterministic movement intent extraction from Hungarian/English player text.

This is intentionally simple and deterministic. LLM can still narrate, but the
engine decides whether movement was requested and which exit is used.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from core.room_graph_models import MovementIntent


class MovementIntentService:
    DIRECTION_ALIASES: Dict[str, str] = {
        "észak": "north",
        "eszak": "north",
        "north": "north",
        "n": "north",
        "dél": "south",
        "del": "south",
        "south": "south",
        "s": "south",
        "kelet": "east",
        "east": "east",
        "e": "east",
        "nyugat": "west",
        "west": "west",
        "w": "west",
        "fel": "up",
        "felfelé": "up",
        "felfele": "up",
        "up": "up",
        "u": "up",
        "le": "down",
        "lefelé": "down",
        "lefele": "down",
        "down": "down",
        "d": "down",
        "be": "in",
        "inside": "in",
        "in": "in",
        "ki": "out",
        "outside": "out",
        "out": "out",
    }

    MOVEMENT_VERBS = {
        "megyek", "megyünk", "indulok", "indulunk", "átmegyek", "átmegyünk",
        "bemegyek", "bemegyünk", "kimegyek", "kimegyünk", "haladok", "haladunk",
        "lépek", "belépek", "move", "go", "enter", "leave", "walk", "head",
    }

    def detect(self, text: str) -> MovementIntent:
        raw = str(text or "")
        normalized = self._normalize(raw)

        direction = self._find_direction(normalized)
        if direction:
            return MovementIntent(requested=True, direction=direction, raw_text=raw)

        if any(verb in normalized.split() for verb in self.MOVEMENT_VERBS):
            hint = self._extract_target_hint(raw)
            return MovementIntent(requested=True, target_room_hint=hint, raw_text=raw)

        return MovementIntent(requested=False, raw_text=raw)

    def _find_direction(self, normalized: str) -> Optional[str]:
        tokens = normalized.split()
        for token in tokens:
            if token in self.DIRECTION_ALIASES:
                return self.DIRECTION_ALIASES[token]
        return None

    @staticmethod
    def _extract_target_hint(raw: str) -> Optional[str]:
        patterns = [
            r"(?:to|towards|into|enter)\s+(?P<hint>.+)$",
            r"(?:a|az)\s+(?P<hint>[^.?!]+?)(?:ba|be|hoz|hez|höz|felé)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match:
                hint = match.group("hint").strip(" .,!?")
                return hint or None
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^0-9a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+", " ", text.lower()).strip()
