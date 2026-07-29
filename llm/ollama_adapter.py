"""
LLM/OLLAMA_ADAPTER.PY
Optional Ollama fallback adapter.

This module uses stdlib urllib only. It performs network calls only at runtime
when selected by ProviderRouter.
"""

from __future__ import annotations

import json
import os
from urllib import request

from llm.base_llm_adapter import BaseLLMAdapter


class OllamaAdapter(BaseLLMAdapter):
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout_seconds: int = 120) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
        self.timeout_seconds = int(timeout_seconds)

    def generate(self, prompt: str) -> str:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response") or "")
