"""
LLM/BASE_LLM_ADAPTER.PY
Minimal provider interface for all LLM backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
