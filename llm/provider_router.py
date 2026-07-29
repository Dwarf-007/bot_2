"""
LLM/PROVIDER_ROUTER.PY
Simple provider fallback router.

Tries providers in order until one returns a non-empty raw response. Providers
must implement generate(prompt: str) -> str.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from llm.base_llm_adapter import BaseLLMAdapter

logger = logging.getLogger(__name__)


class ProviderRouter(BaseLLMAdapter):
    def __init__(self, providers: Iterable[BaseLLMAdapter], fallback_text: Optional[str] = None) -> None:
        self.providers: List[BaseLLMAdapter] = [provider for provider in providers if provider is not None]
        self.fallback_text = fallback_text or self._fallback_json("No LLM provider returned a usable response.")

    def generate(self, prompt: str) -> str:
        for provider in self.providers:
            try:
                text = provider.generate(prompt)
            except Exception:
                logger.exception("LLM provider failed: %r", provider)
                continue
            if text and str(text).strip():
                return str(text)
        return self.fallback_text

    @staticmethod
    def _fallback_json(reason: str) -> str:
        safe_reason = reason.replace('"', "'")
        return (
            '{'
            '"narrative":"A narrációs modell jelenleg nem elérhető. Kérlek ismételd meg az akciódat rövidebben.",'
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
