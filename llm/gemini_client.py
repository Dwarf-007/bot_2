"""
LLM/GEMINI_CLIENT.PY
Gemini adapter with multi-key rotation and quota/rate-limit failover.

Environment variables:
- GEMINI_API_KEYS=key1,key2,key3
- GOOGLE_API_KEYS=key1,key2,key3
- GEMINI_API_KEY=single_key
- GOOGLE_API_KEY=single_key
- GEMINI_API_KEY_1 ... GEMINI_API_KEY_20
- GOOGLE_API_KEY_1 ... GOOGLE_API_KEY_20
- GEMINI_MODEL, default: gemini-2.5-flash
"""

from __future__ import annotations

import os
import time
from typing import Iterable, Optional

from llm.base_llm_adapter import BaseLLMAdapter
from llm.key_manager import GeminiKeyManager


class GeminiClientService(BaseLLMAdapter):
    def __init__(
        self,
        api_keys: Optional[Iterable[str]] = None,
        key_manager: Optional[GeminiKeyManager] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 60,
        max_retries_per_key: int = 1,
        max_total_attempts: int = 8,
        key_cooldown_seconds: int = 300,
    ) -> None:
        self.key_manager = key_manager or GeminiKeyManager(api_keys, cooldown_seconds=key_cooldown_seconds)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout_seconds = int(timeout_seconds)
        self.max_retries_per_key = max(1, int(max_retries_per_key or 1))
        self.max_total_attempts = max(1, int(max_total_attempts or 8))

    def generate(self, prompt: str) -> str:
        if not self.key_manager.has_keys():
            return self._fallback_json("Gemini API key is missing.")

        last_error = "unknown error"
        attempts = 0
        used_keys: set[str] = set()

        while attempts < self.max_total_attempts:
            api_key = self.key_manager.next_key()
            if not api_key:
                break

            used_keys.add(api_key)
            for retry_index in range(self.max_retries_per_key):
                attempts += 1
                try:
                    text = self._generate_once(api_key, prompt)
                    self.key_manager.report_success(api_key)
                    return text
                except Exception as exc:
                    last_error = str(exc)
                    if self._is_quota_or_rate_limit_error(exc):
                        self.key_manager.report_failure(api_key)
                        break
                    if retry_index + 1 < self.max_retries_per_key:
                        time.sleep(1 + retry_index)
                if attempts >= self.max_total_attempts:
                    break

            # If every known key has been tried and none is currently available, stop.
            if len(used_keys) >= len(self.key_manager.keys) and self.key_manager.available_count() == 0:
                break

        return self._fallback_json(f"Gemini provider failure after key rotation: {last_error}")

    def _generate_once(self, api_key: str, prompt: str) -> str:
        from google import genai  # lazy import so non-LLM tests can import this module

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text and str(text).strip():
            return str(text)
        raise RuntimeError("Gemini returned empty text.")

    @staticmethod
    def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
        text = repr(exc).lower()
        markers = [
            "quota",
            "rate limit",
            "ratelimit",
            "429",
            "resource_exhausted",
            "too many requests",
        ]
        return any(marker in text for marker in markers)

    @staticmethod
    def _fallback_json(reason: str) -> str:
        safe_reason = reason.replace('"', "'")
        return (
            '{'
            '"narrative":"A narrációs modell jelenleg nem válaszol megbízhatóan. Kérlek ismételd meg az akciódat rövidebben.",'
            '"required_check":"None",'
            '"dc":0,'
            '"next_room_id":null,'
            '"xp_reward":0,'
            '"milestone_reached":false,'
            '"inventory_update":{"gold":0.0,"items":{},"ammo":{}},'
            '"avrae_sync_damage":null,'
            '"secret_messages":[],'
            '"rest_consequence":{"rest_type":"NONE","status":"NONE","ambush_monster":null},'
            '"combat_start":{"enabled":false,"monsters":[],"xp_reward_total":0,"encounter_type":"FALLBACK","difficulty":"STANDARD"},'
            '"confidence":"low",'
            '"source_usage":"fallback",'
            '"needs_clarification":true,'
            f'"dm_notes":["{safe_reason}"]'
            '}'
        )
