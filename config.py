"""
CONFIG.PY
Centralized runtime configuration for the AI DM engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import List, Optional


@dataclass(frozen=True)
class AppConfig:
    discord_token: str
    discord_command_prefix: str = "!"
    database_file: str = "campaigns.db"
    gemini_api_keys: List[str] = field(default_factory=list)
    gemini_model: str = "gemini-2.5-flash"
    gemini_key_cooldown_seconds: int = 300
    gemini_max_total_attempts: int = 8
    llm_enable_ollama_fallback: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct-q4_K_M"
    bestiary_path: str = "data/bestiary.json"
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @property
    def has_llm_key(self) -> bool:
        return bool(self.gemini_api_keys)


def load_config(require_discord_token: bool = True) -> AppConfig:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if require_discord_token and not token:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

    return AppConfig(
        discord_token=token,
        discord_command_prefix=os.getenv("DISCORD_COMMAND_PREFIX", "!").strip() or "!",
        database_file=os.getenv("AI_DM_DATABASE_FILE", "campaigns.db").strip() or "campaigns.db",
        gemini_api_keys=_load_gemini_keys(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        gemini_key_cooldown_seconds=_safe_int(os.getenv("GEMINI_KEY_COOLDOWN_SECONDS"), 300),
        gemini_max_total_attempts=_safe_int(os.getenv("GEMINI_MAX_TOTAL_ATTEMPTS"), 8),
        llm_enable_ollama_fallback=_env_bool("LLM_ENABLE_OLLAMA_FALLBACK", False),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434",
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct").strip() or "qwen2.5:14b-instruct",
        bestiary_path=os.getenv("AI_DM_BESTIARY_PATH", "data/bestiary.json").strip() or "data/bestiary.json",
        log_level=os.getenv("AI_DM_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        log_file=os.getenv("AI_DM_LOG_FILE") or None,
    )


def _load_gemini_keys() -> List[str]:
    keys: List[str] = []
    for env_name in ["GEMINI_API_KEYS", "GOOGLE_API_KEYS"]:
        keys.extend(_split_key_list(os.getenv(env_name, "")))
    for env_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        value = os.getenv(env_name, "").strip()
        if value:
            keys.append(value)
    for prefix in ["GEMINI_API_KEY_", "GOOGLE_API_KEY_"]:
        for index in range(1, 21):
            value = os.getenv(f"{prefix}{index}", "").strip()
            if value:
                keys.append(value)
    return _dedupe(keys)


def _split_key_list(value: str) -> List[str]:
    if not value:
        return []
    normalized = value.replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _dedupe(values: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
