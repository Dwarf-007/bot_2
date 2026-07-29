"""
SERVICES/REST_INTENT_SERVICE.PY
Deterministic rest intent detection from Hungarian/English player text.
"""

from __future__ import annotations

import re

from core.rest_models import RestIntent


class RestIntentService:
    SHORT_REST_PATTERNS = [
        r"\bshort\s+rest\b",
        r"\brövid\s+pihenő\b",
        r"\brovid\s+piheno\b",
        r"\brövidet\s+pihen",
        r"\brovidet\s+pihen",
    ]
    LONG_REST_PATTERNS = [
        r"\blong\s+rest\b",
        r"\bhosszú\s+pihenő\b",
        r"\bhosszu\s+piheno\b",
        r"\bhosszút\s+pihen",
        r"\bhosszut\s+pihen",
        r"\baludni\b",
        r"\blefekszünk\b",
        r"\blefekszunk\b",
    ]

    def detect(self, text: str) -> RestIntent:
        raw = str(text or "")
        normalized = raw.lower()

        if self._matches_any(normalized, self.LONG_REST_PATTERNS):
            return RestIntent(requested=True, rest_type="LONG", raw_text=raw)
        if self._matches_any(normalized, self.SHORT_REST_PATTERNS):
            return RestIntent(requested=True, rest_type="SHORT", raw_text=raw)
        return RestIntent(requested=False, rest_type="NONE", raw_text=raw)

    @staticmethod
    def _matches_any(text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
