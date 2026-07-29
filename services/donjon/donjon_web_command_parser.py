"""Parser for Donjon web generation CLI/Discord arguments."""

from __future__ import annotations

import shlex
from typing import Optional

from services.donjon.donjon_web_config import describe_donjon_options
from services.generators.web_automation_models import WebGenerationRequest


class DonjonWebCommandParser:
    def parse(self, raw: str, default_output_root: str = "campaigns/web") -> tuple[WebGenerationRequest, dict]:
        tokens = shlex.split(str(raw or ""))
        if not tokens:
            raise ValueError("Expected: <campaign_id> [options]")
        if tokens[0].lower() in {"donjon", "donjon_web"}:
            tokens = tokens[1:]
        if not tokens:
            raise ValueError("Missing campaign_id")
        campaign_id = tokens[0]
        campaign_name: Optional[str] = None
        output_dir: Optional[str] = None
        url = "https://donjon.bin.sh/5e/dungeon/"
        headless = True
        enrich = True
        import_to_runtime = False
        clear_rag = False
        max_rooms: Optional[int] = None
        fields = {}

        i = 1
        while i < len(tokens):
            token = tokens[i]
            if token in {"--name", "--campaign-name"}:
                campaign_name = self._next(tokens, i, token); i += 2
            elif token == "--url":
                url = self._next(tokens, i, token); i += 2
            elif token == "--output-dir":
                output_dir = self._next(tokens, i, token); i += 2
            elif token == "--headed":
                headless = False; i += 1
            elif token == "--headless":
                headless = True; i += 1
            elif token == "--no-enrich":
                enrich = False; i += 1
            elif token == "--import":
                import_to_runtime = True; i += 1
            elif token == "--clear-rag":
                clear_rag = True; i += 1
            elif token == "--max-rooms":
                max_rooms = int(self._next(tokens, i, token)); i += 2
            elif token.startswith("--"):
                key = token[2:].replace("-", "_")
                fields[key] = self._next(tokens, i, token); i += 2
            else:
                raise ValueError(f"Unknown argument: {token}")

        req = WebGenerationRequest(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            output_dir=output_dir or f"{default_output_root}/{campaign_id}",
            url=url,
            headless=headless,
            seed=fields.pop("seed", None),
            dungeon_name=fields.pop("dungeon_name", campaign_name),
            dungeon_level=fields.pop("dungeon_level", None),
            party_level=fields.pop("party_level", None),
            size=fields.pop("size", None),
            layout=fields.pop("layout", None),
            theme=fields.pop("theme", None),
            peripheral_egress=fields.pop("peripheral_egress", None),
            room_layout=fields.pop("room_layout", None),
            room_size=fields.pop("room_size", None),
            doors=fields.pop("doors", None),
            corridor_layout=fields.pop("corridor_layout", None),
            remove_deadends=fields.pop("remove_deadends", None),
            stairs=fields.pop("stairs", None),
            map_style=fields.pop("map_style", None),
            grid=fields.pop("grid", None),
            motif=fields.pop("motif", None),
            room_polymorph=fields.pop("room_polymorph", None),
            infest=fields.pop("infest", None),
            n_pc=fields.pop("n_pc", None),
            image_size=fields.pop("image_size", None),
            custom_fields=fields,
        )
        opts = {"enrich": enrich, "import_to_runtime": import_to_runtime, "clear_rag": clear_rag, "max_rooms": max_rooms}
        return req, opts

    @staticmethod
    def _next(tokens: list[str], index: int, option: str) -> str:
        if index + 1 >= len(tokens):
            raise ValueError(f"Missing value for {option}")
        return tokens[index + 1]

    @staticmethod
    def option_catalog_text() -> str:
        """Full Donjon option catalog as text (for the LLM / help output)."""
        return describe_donjon_options()
