"""
SERVICES/GENERATORS/GENERATE_COMMAND_PARSER.PY

Small parser for Discord/admin generation commands.

Supported examples:
    donjon_json sakka ./sakka.json --name "Sakka" --theme "lich dungeon" --enrich --import
    sakka ./sakka.json --name "Sakka" --no-enrich

The parser stays dependency-free so it can be tested without discord.py.
"""

from __future__ import annotations

import shlex
from typing import Optional

from services.generators.generation_orchestrator import GenerateCampaignRequest


class GenerateCommandParser:
    def parse(self, raw: str, default_output_root: str = "campaigns") -> GenerateCampaignRequest:
        tokens = shlex.split(str(raw or ""))
        if not tokens:
            raise ValueError("Missing generation arguments. Expected: <campaign_id> <source_path> [options]")

        provider = "donjon_json"
        if tokens[0].lower() in {"donjon", "donjon_json"}:
            provider = "donjon_json"
            tokens = tokens[1:]

        if len(tokens) < 2:
            raise ValueError("Expected: [donjon_json] <campaign_id> <source_path> [--name ...] [--theme ...]")

        campaign_id = tokens[0]
        source_path = tokens[1]
        campaign_name: Optional[str] = None
        theme = "ancient cursed dungeon"
        tone = "grim exploration"
        enrich = True
        import_to_runtime = False
        clear_rag = False
        output_dir: Optional[str] = None
        max_rooms: Optional[int] = None
        party_size: Optional[int] = None
        party_level: Optional[int] = None

        i = 2
        while i < len(tokens):
            token = tokens[i]
            if token in {"--name", "--campaign-name"}:
                campaign_name = self._next(tokens, i, token)
                i += 2
            elif token == "--theme":
                theme = self._next(tokens, i, token)
                i += 2
            elif token == "--tone":
                tone = self._next(tokens, i, token)
                i += 2
            elif token == "--output-dir":
                output_dir = self._next(tokens, i, token)
                i += 2
            elif token == "--max-rooms":
                max_rooms = int(self._next(tokens, i, token))
                i += 2
            elif token == "--no-enrich":
                enrich = False
                i += 1
            elif token == "--enrich":
                enrich = True
                i += 1
            elif token == "--import":
                import_to_runtime = True
                i += 1
            elif token == "--clear-rag":
                clear_rag = True
                i += 1
            elif token == "--party-size":
                party_size = int(self._next(tokens, i, token))
                i += 2
            elif token == "--party-level":
                party_level = int(self._next(tokens, i, token))
                i += 2
            else:
                raise ValueError(f"Unknown generate option: {token}")

        output_dir = output_dir or f"{default_output_root}/{campaign_id}"
        return GenerateCampaignRequest(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            provider=provider,
            source_path=source_path,
            output_dir=output_dir,
            theme=theme,
            tone=tone,
            enrich=enrich,
            import_to_runtime=import_to_runtime,
            clear_rag=clear_rag,
            max_rooms=max_rooms,
            party_size=party_size,
            party_level=party_level,
        )

    @staticmethod
    def _next(tokens: list[str], index: int, option: str) -> str:
        if index + 1 >= len(tokens):
            raise ValueError(f"Missing value for {option}")
        return tokens[index + 1]
