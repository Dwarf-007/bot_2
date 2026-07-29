"""
SERVICES/GENERATORS/DONJON_WEB_PIPELINE.PY

Convenience pipeline:
Donjon web automation -> Donjon JSON file -> Sprint 4 GenerationOrchestrator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from services.donjon.donjon_web_provider import DonjonWebProvider
from services.generators.generation_orchestrator import GenerateCampaignRequest, GenerationOrchestrator, GeneratedCampaignResult
from services.generators.web_automation_models import WebGenerationRequest, WebGenerationResult


def _parse_optional_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class DonjonWebPipeline:
    def __init__(self, runtime: Any = None, llm_adapter: Any = None, provider: Optional[DonjonWebProvider] = None) -> None:
        self.runtime = runtime
        self.llm_adapter = llm_adapter
        self.provider = provider or DonjonWebProvider()

    def generate_campaign_from_web(
        self,
        web_request: WebGenerationRequest,
        enrich: bool = True,
        import_to_runtime: bool = False,
        clear_rag: bool = False,
        max_rooms: Optional[int] = None,
    ) -> dict:
        web_result = self.provider.generate(web_request)
        if not web_result.json_file:
            raise RuntimeError(
                "Donjon web generation completed but no JSON file was downloaded. "
                "Check donjon_result.html, donjon_result.png and selector configuration."
            )

        orchestrator = GenerationOrchestrator(runtime=self.runtime, llm_adapter=self.llm_adapter)
        party_size = _parse_optional_int((web_request.custom_fields or {}).get("party_size"))
        party_level = _parse_optional_int(web_request.party_level)
        campaign_result = orchestrator.generate_campaign(
            GenerateCampaignRequest(
                campaign_id=web_request.campaign_id,
                campaign_name=web_request.campaign_name or web_request.dungeon_name or web_request.campaign_id,
                provider="donjon_json",
                source_path=web_result.json_file,
                output_dir=str(Path(web_request.output_dir) / "campaign_bundle"),
                theme=web_request.theme or "ancient cursed dungeon",
                tone="grim exploration",
                enrich=enrich,
                import_to_runtime=import_to_runtime,
                clear_rag=clear_rag,
                max_rooms=max_rooms,
                party_size=party_size,
                party_level=party_level,
                metadata={"web_generation": web_result.to_dict()},
            )
        )
        result = {"web_generation": web_result.to_dict(), "campaign_generation": campaign_result.to_dict()}
        Path(web_request.output_dir).mkdir(parents=True, exist_ok=True)
        (Path(web_request.output_dir) / "donjon_web_pipeline_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result
