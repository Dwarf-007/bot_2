"""
LLM/KEY_MANAGER.PY
Provider API key rotation utilities.

Supports:
- comma-separated env var style key lists
- numbered env var style key lists
- round-robin selection
- temporary key cooldown after quota/rate-limit failures

No network calls here.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Iterable, List, Optional


@dataclass
class KeyState:
    key: str
    disabled_until: float = 0.0
    failure_count: int = 0


class GeminiKeyManager:
    def __init__(
        self,
        keys: Optional[Iterable[str]] = None,
        cooldown_seconds: int = 300,
    ) -> None:
        normalized = self._normalize_keys(keys if keys is not None else self.load_keys_from_env())
        self._states: List[KeyState] = [KeyState(key=key) for key in normalized]
        self._index = 0
        self.cooldown_seconds = max(1, int(cooldown_seconds or 300))

    @property
    def keys(self) -> List[str]:
        return [state.key for state in self._states]

    def has_keys(self) -> bool:
        return bool(self._states)

    def next_key(self) -> Optional[str]:
        if not self._states:
            return None

        now = time.time()
        total = len(self._states)
        for _ in range(total):
            state = self._states[self._index]
            self._index = (self._index + 1) % total
            if state.disabled_until <= now:
                return state.key
        return None

    def report_success(self, key: str) -> None:
        state = self._find_state(key)
        if state:
            state.failure_count = 0
            state.disabled_until = 0.0

    def report_failure(self, key: str, cooldown: Optional[int] = None) -> None:
        state = self._find_state(key)
        if not state:
            return
        state.failure_count += 1
        state.disabled_until = time.time() + int(cooldown or self.cooldown_seconds)

    def available_count(self) -> int:
        now = time.time()
        return sum(1 for state in self._states if state.disabled_until <= now)

    def _find_state(self, key: str) -> Optional[KeyState]:
        for state in self._states:
            if state.key == key:
                return state
        return None

    @classmethod
    def load_keys_from_env(cls) -> List[str]:
        keys: List[str] = []

        # Preferred multi-key variables.
        for env_name in ["GEMINI_API_KEYS", "GOOGLE_API_KEYS"]:
            value = os.getenv(env_name, "")
            keys.extend(cls._split_key_list(value))

        # Backward-compatible single key variables.
        for env_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            value = os.getenv(env_name, "")
            if value.strip():
                keys.append(value.strip())

        # Numbered variables: GEMINI_API_KEY_1..20, GOOGLE_API_KEY_1..20.
        for prefix in ["GEMINI_API_KEY_", "GOOGLE_API_KEY_"]:
            for index in range(1, 21):
                value = os.getenv(f"{prefix}{index}", "")
                if value.strip():
                    keys.append(value.strip())

        return cls._normalize_keys(keys)

    @staticmethod
    def _split_key_list(value: str) -> List[str]:
        if not value:
            return []
        # Allow comma, semicolon, or newline separated values.
        normalized = value.replace(";", ",").replace("\n", ",")
        return [part.strip() for part in normalized.split(",") if part.strip()]

    @staticmethod
    def _normalize_keys(keys: Iterable[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for key in keys or []:
            text = str(key or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result
