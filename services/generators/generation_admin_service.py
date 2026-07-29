"""
SERVICES/GENERATORS/GENERATION_ADMIN_SERVICE.PY

Runtime service wrapper for Discord/admin commands.
"""

from __future__ import annotations

from services.generators.generate_command_parser import GenerateCommandParser
from services.generators.generation_orchestrator import GenerationOrchestrator


class GenerationAdminService:
    def __init__(self, runtime=None, llm_adapter=None, default_output_root: str = "campaigns") -> None:
        self.runtime = runtime
        self.default_output_root = default_output_root
        self.parser = GenerateCommandParser()
        self.orchestrator = GenerationOrchestrator(runtime=runtime, llm_adapter=llm_adapter)

    def generate_text(self, raw_args: str) -> str:
        request = self.parser.parse(raw_args, default_output_root=self.default_output_root)
        result = self.orchestrator.generate_campaign(request)
        return result.to_text()

    @staticmethod
    def help_text() -> str:
        return (
            "**Generate command**\n"
            "`!dm_generate donjon_json <campaign_id> <path/to/donjon.json> --name \"Campaign Name\" --theme \"lich dungeon\" --enrich --import --clear-rag`\n\n"
            "Examples:\n"
            "`!dm_generate donjon_json sakka ./The Chambers of Sakka the Crimson 01.json --name \"The Chambers of Sakka\" --theme \"lich-haunted crimson dungeon\" --import --clear-rag`\n"
            "`!dm_generate sakka ./sakka.json --no-enrich`"
        )
