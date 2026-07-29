
"""
SERVICES/RUNTIME_HEALTH_SERVICE.PY
Runtime diagnostics for DB schema, imports, LLM provider config, RAG status, and campaign data.
Refactor 20 compatibility version.
"""

from __future__ import annotations

import importlib
from typing import Iterable, List

from models.runtime_health import HealthCheckItem, RuntimeHealthReport


class RuntimeHealthService:
    REQUIRED_MODULES = [
        "app.bootstrap", "bot.bot_core", "bot.admin_commands",
        "core.game_events", "core.turn_output", "core.room_graph_models",
        "repositories.channel_repository", "repositories.location_repository",
        "repositories.rag_chunk_repository", "repositories.campaign_repository",
        "repositories.campaign_progress_repository", "repositories.room_alias_repository",
        "services.game_turn_service", "services.context_service", "services.rag_runtime",
        "services.progress_service", "services.room_alias_service", "services.room_graph_builder",
        "services.navigation_engine", "llm.gemini_client", "llm.provider_router", "avrae.avrae_parser",
    ]

    def __init__(self, config=None, campaign_repo=None, channel_repo=None, location_repo=None, rag_chunk_repo=None, room_alias_repo=None, progress_repo=None, memory_repo=None, llm_adapter=None) -> None:
        self.config = config
        self.campaign_repo = campaign_repo
        self.channel_repo = channel_repo
        self.location_repo = location_repo
        self.rag_chunk_repo = rag_chunk_repo
        self.room_alias_repo = room_alias_repo
        self.progress_repo = progress_repo
        self.memory_repo = memory_repo
        self.llm_adapter = llm_adapter

    def run_all(self, campaign_id: str | None = None, channel_id: str | None = None) -> RuntimeHealthReport:
        checks: List[HealthCheckItem] = []
        checks.extend(self.check_imports())
        checks.extend(self.check_repositories())
        checks.append(self.check_llm_config())
        checks.append(self.check_campaign_data(campaign_id or "default"))
        if channel_id:
            checks.append(self.check_channel_state(channel_id))
        return RuntimeHealthReport(status=self._aggregate(checks), checks=checks)

    def check_imports(self, modules: Iterable[str] | None = None) -> List[HealthCheckItem]:
        checks: List[HealthCheckItem] = []
        for module_name in modules or self.REQUIRED_MODULES:
            try:
                importlib.import_module(module_name)
                checks.append(HealthCheckItem(name=f"import:{module_name}", status="OK", message="import sikeres"))
            except Exception as exc:
                checks.append(HealthCheckItem(name=f"import:{module_name}", status="FAIL", message=repr(exc)))
        return checks

    def check_repositories(self) -> List[HealthCheckItem]:
        checks: List[HealthCheckItem] = []
        for name, repo in [
            ("campaign_repo", self.campaign_repo),
            ("rag_chunk_repo", self.rag_chunk_repo),
            ("room_alias_repo", self.room_alias_repo),
            ("progress_repo", self.progress_repo),
            ("memory_repo", self.memory_repo),
            ("location_repo", self.location_repo),
        ]:
            if repo is None:
                checks.append(HealthCheckItem(name=name, status="WARN", message="repository nincs bekötve"))
                continue
            try:
                if hasattr(repo, "ensure_schema"):
                    repo.ensure_schema()
                checks.append(HealthCheckItem(name=name, status="OK", message="schema elérhető"))
            except Exception as exc:
                checks.append(HealthCheckItem(name=name, status="FAIL", message=repr(exc)))
        return checks

    def check_llm_config(self) -> HealthCheckItem:
        if self.config is None:
            return HealthCheckItem(name="llm_config", status="WARN", message="config nincs átadva")
        key_count = len(getattr(self.config, "gemini_api_keys", []) or [])
        ollama = bool(getattr(self.config, "llm_enable_ollama_fallback", False))
        if key_count > 0:
            return HealthCheckItem(name="llm_config", status="OK", message="Gemini kulcs(ok) konfigurálva", details={"gemini_key_count": key_count, "ollama_fallback": ollama})
        if ollama:
            return HealthCheckItem(name="llm_config", status="WARN", message="nincs Gemini kulcs, de Ollama fallback engedélyezett")
        return HealthCheckItem(name="llm_config", status="WARN", message="nincs LLM kulcs/fallback konfigurálva")

    def check_campaign_data(self, campaign_id: str) -> HealthCheckItem:
        details = {"campaign_id": campaign_id, "campaign_registered": False, "rooms": 0, "rag_chunks": 0, "aliases": 0, "scenes": 0}
        try:
            if self.campaign_repo:
                details["campaign_registered"] = self.campaign_repo.get_campaign(campaign_id) is not None
            if self.location_repo:
                details["rooms"] = len(self.location_repo.list_rooms(campaign_id=campaign_id))
            if self.rag_chunk_repo:
                details["rag_chunks"] = len(self.rag_chunk_repo.list_chunks(campaign_id=campaign_id, limit=10000))
            if self.room_alias_repo:
                if hasattr(self.room_alias_repo, "count_aliases"):
                    details["aliases"] = self.room_alias_repo.count_aliases(campaign_id)
                else:
                    details["aliases"] = len(self.room_alias_repo.search(campaign_id, "", limit=50))
            if self.progress_repo:
                details["scenes"] = len(self.progress_repo.list_scenes(campaign_id))
        except Exception as exc:
            return HealthCheckItem(name="campaign_data", status="FAIL", message=repr(exc), details=details)
        if not details["campaign_registered"]:
            return HealthCheckItem(name="campaign_data", status="WARN", message="kampány nincs regisztrálva", details=details)
        if int(details["rooms"] or 0) == 0 and int(details["rag_chunks"] or 0) == 0:
            return HealthCheckItem(name="campaign_data", status="WARN", message="nincs importált room vagy RAG adat", details=details)
        return HealthCheckItem(name="campaign_data", status="OK", message="kampányadatok elérhetőek", details=details)

    def check_channel_state(self, channel_id: str) -> HealthCheckItem:
        if not self.channel_repo:
            return HealthCheckItem(name="channel_state", status="WARN", message="ChannelRepository nincs bekötve")
        try:
            state = self.channel_repo.get_state(channel_id)
            return HealthCheckItem(name="channel_state", status="OK", message="channel state olvasható", details={"channel_id": channel_id, "campaign_id": state.get("campaign_id", "default"), "location": state.get("current_location_id"), "mode": state.get("mode")})
        except Exception as exc:
            return HealthCheckItem(name="channel_state", status="FAIL", message=repr(exc))

    @staticmethod
    def _aggregate(checks: List[HealthCheckItem]) -> str:
        statuses = {item.status for item in checks}
        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses:
            return "WARN"
        return "OK"
