"""
SERVICES/GENERATORS/GENERATION_ORCHESTRATOR.PY

Sprint 4: High-level orchestration for generated campaigns.

This service wires together Sprint 1, Sprint 2 and Sprint 3:

Donjon JSON
  -> GeneratedDungeon
  -> campaign bundle files
  -> optional/deterministic enrichment
  -> optional import into the existing repository pipeline

The orchestrator is intentionally usable from both CLI and Discord command layers.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GenerateCampaignRequest:
    campaign_id: str
    campaign_name: Optional[str] = None
    provider: str = "donjon_json"
    source_path: Optional[str] = None
    output_dir: str = "campaigns/generated"
    theme: str = "ancient cursed dungeon"
    tone: str = "grim exploration"
    enrich: bool = True
    import_to_runtime: bool = False
    clear_rag: bool = False
    max_rooms: Optional[int] = None
    party_size: Optional[int] = None
    party_level: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedCampaignResult:
    campaign_id: str
    campaign_name: str
    provider: str
    output_dir: str
    generated_summary: Dict[str, Any] = field(default_factory=dict)
    bundle_files: Dict[str, str] = field(default_factory=dict)
    enriched_files: Dict[str, str] = field(default_factory=dict)
    imported: bool = False
    message: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            "**Generated campaign ready**",
            f"Campaign: `{self.campaign_id}` — {self.campaign_name}",
            f"Provider: `{self.provider}`",
            f"Output dir: `{self.output_dir}`",
        ]
        if self.generated_summary:
            lines.append(
                "Summary: "
                + ", ".join(f"{k}={v}" for k, v in self.generated_summary.items() if k in {"room_count", "connection_count", "door_count", "trap_count"})
            )
        if self.enriched_files:
            lines.append("Enrichment: `enabled`")
        else:
            lines.append("Enrichment: `disabled`")
        lines.append(f"Imported into runtime: `{'yes' if self.imported else 'no'}`")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        if self.message:
            lines.append(self.message)
        return "\n".join(lines)


class GenerationOrchestrator:
    def __init__(self, runtime: Any = None, llm_adapter: Any = None) -> None:
        self.runtime = runtime
        self.llm_adapter = llm_adapter

    def generate_campaign(self, request: GenerateCampaignRequest) -> GeneratedCampaignResult:
        provider = str(request.provider or "donjon_json").strip().lower()
        if provider != "donjon_json":
            raise ValueError(f"Unsupported provider in Sprint 4: {provider!r}. Supported: 'donjon_json'.")
        if not request.source_path:
            raise ValueError("source_path is required for provider='donjon_json' in Sprint 4")

        campaign_id = str(request.campaign_id or "").strip()
        if not campaign_id:
            raise ValueError("campaign_id is required")
        campaign_name = request.campaign_name or campaign_id
        output_root = Path(request.output_dir)
        raw_dir = output_root / "raw_bundle"
        final_dir = output_root / "bundle"
        output_root.mkdir(parents=True, exist_ok=True)

        from services.donjon.donjon_json_importer import DonjonJsonImporter
        from services.generators.campaign_bundle_builder import CampaignBundleBuilder

        importer = DonjonJsonImporter()
        dungeon = importer.import_file(request.source_path, dungeon_id=campaign_id, title=campaign_name)
        generated_path = output_root / "generated_dungeon.json"
        generated_path.write_text(json.dumps(dungeon.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        builder = CampaignBundleBuilder()
        bundle_files = builder.write_bundle(dungeon, campaign_id=campaign_id, campaign_name=campaign_name, output_dir=raw_dir)

        enriched_files: dict[str, str] = {}
        active_bundle_dir = raw_dir
        if request.enrich:
            from services.generators.campaign_enricher import CampaignEnricher

            enricher = CampaignEnricher(llm_adapter=self.llm_adapter)
            enriched_files = enricher.write_enriched_bundle(
                input_dir=raw_dir,
                output_dir=final_dir,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                theme=request.theme,
                tone=request.tone,
                use_llm=bool(self.llm_adapter),
                max_rooms=request.max_rooms,
            )
            active_bundle_dir = final_dir
        else:
            if final_dir.exists():
                shutil.rmtree(final_dir)
            shutil.copytree(raw_dir, final_dir)
            active_bundle_dir = final_dir

        imported = False
        warnings: list[str] = []
        if request.import_to_runtime:
            if not self.runtime:
                warnings.append("import_to_runtime=True was requested, but no runtime was provided.")
            else:
                self._import_bundle_into_runtime(
                    runtime=self.runtime,
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    bundle_dir=active_bundle_dir,
                    clear_rag=request.clear_rag,
                    party_size=request.party_size,
                    party_level=request.party_level,
                )
                imported = True

        result = GeneratedCampaignResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            provider=provider,
            output_dir=str(active_bundle_dir),
            generated_summary=dungeon.summary(),
            bundle_files=bundle_files,
            enriched_files=enriched_files,
            imported=imported,
            message="Use tools/import_campaign_bundle.py to import the generated bundle if it was not imported automatically.",
            warnings=warnings,
        )
        (output_root / "generation_result.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _import_bundle_into_runtime(self, runtime: Any, campaign_id: str, campaign_name: str, bundle_dir: Path, clear_rag: bool = False, party_size: Optional[int] = None, party_level: Optional[int] = None) -> None:
        """Import using runtime repositories directly, mirroring tools/import_campaign_bundle.py."""
        room_data = self._read_json(bundle_dir / "room_data.json", {"rooms": []})
        room_lookup = self._read_json(bundle_dir / "room_lookup.json", {})
        rag_index = self._read_json(bundle_dir / "rag_index.json", {"chunks": []})
        toc_index = self._read_json(bundle_dir / "toc_index.json", {"entries": []})

        runtime.campaign_service.ensure_campaign(
            campaign_id,
            campaign_name,
            party_size=party_size,
            party_level=party_level,
        )
        rooms = room_data.get("rooms", []) if isinstance(room_data, dict) else []
        for room in rooms:
            room.setdefault("campaign_id", campaign_id)
            runtime.location_repo.upsert_room(room)
            if getattr(runtime, "room_alias_service", None):
                runtime.room_alias_service.ensure_room_aliases_from_room(campaign_id, room)
        if getattr(runtime, "room_alias_repo", None):
            runtime.room_alias_repo.import_lookup(campaign_id, room_lookup)
        if clear_rag and getattr(runtime, "rag_chunk_repo", None):
            runtime.rag_chunk_repo.delete_campaign_chunks(campaign_id)
        if getattr(runtime, "rag_chunk_repo", None):
            for chunk in (rag_index.get("chunks", []) if isinstance(rag_index, dict) else []):
                chunk.setdefault("campaign_id", campaign_id)
                runtime.rag_chunk_repo.upsert_chunk(chunk)
            runtime.rag_chunk_repo.rebuild_fts(campaign_id)
        if getattr(runtime, "progress_service", None):
            runtime.progress_service.import_toc_entries(campaign_id, toc_index if isinstance(toc_index, dict) else {})
            runtime.progress_service.ensure_scenes_from_rooms(campaign_id, rooms)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
