"""
SERVICES/GENERATORS/LEGACY_RUNTIME_ADAPTER.PY

Small compatibility helpers for using Sprint 4-8 generator services with the
older but fuller AI DM runtime branch uploaded by the user.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class LegacyRuntimeGeneratorAdapter:
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def import_bundle_dir(self, campaign_id: str, campaign_name: str, bundle_dir: str | Path, clear_rag: bool = False) -> Dict[str, int]:
        root = Path(bundle_dir)
        if not root.exists():
            raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")
        room_data = self._read_json(root / "room_data.json", {"rooms": []})
        room_lookup = self._read_json(root / "room_lookup.json", {})
        rag_index = self._read_json(root / "rag_index.json", {"chunks": []})
        toc_index = self._read_json(root / "toc_index.json", {"entries": []})
        return self.import_bundle_data(campaign_id, campaign_name, room_data, room_lookup, rag_index, toc_index, clear_rag=clear_rag)

    def import_bundle_data(
        self,
        campaign_id: str,
        campaign_name: str,
        room_data: Dict[str, Any],
        room_lookup: Dict[str, Any],
        rag_index: Dict[str, Any],
        toc_index: Dict[str, Any],
        clear_rag: bool = False,
    ) -> Dict[str, int]:
        runtime = self.runtime
        runtime.campaign_service.ensure_campaign(campaign_id, campaign_name)

        rooms = room_data.get("rooms", []) if isinstance(room_data, dict) else []
        room_count = 0
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room.setdefault("campaign_id", campaign_id)
            room.setdefault("raw", dict(room))
            room.setdefault("monsters", room.get("monsters", []))
            runtime.location_repo.upsert_room(room)
            if getattr(runtime, "room_alias_service", None):
                runtime.room_alias_service.ensure_room_aliases_from_room(campaign_id, room)
            room_count += 1

        alias_count = 0
        if getattr(runtime, "room_alias_service", None) and isinstance(room_lookup, dict):
            alias_count = runtime.room_alias_service.import_lookup(campaign_id, room_lookup)

        chunk_count = 0
        chunks = rag_index.get("chunks", rag_index.get("entries", [])) if isinstance(rag_index, dict) else []
        if clear_rag and getattr(runtime, "rag_chunk_repo", None):
            runtime.rag_chunk_repo.delete_campaign_chunks(campaign_id)
        if getattr(runtime, "rag_chunk_repo", None):
            for index, chunk in enumerate(chunks or [], start=1):
                if not isinstance(chunk, dict):
                    continue
                chunk.setdefault("campaign_id", campaign_id)
                chunk.setdefault("chunk_id", str(chunk.get("id") or index))
                runtime.rag_chunk_repo.upsert_chunk(chunk)
                chunk_count += 1
            runtime.rag_chunk_repo.rebuild_fts(campaign_id=campaign_id)

        scene_count = 0
        if getattr(runtime, "progress_service", None):
            scene_count += runtime.progress_service.import_toc_entries(campaign_id, toc_index if isinstance(toc_index, dict) else {})
            scene_count += runtime.progress_service.ensure_scenes_from_rooms(campaign_id, rooms)

        return {"rooms": room_count, "aliases": alias_count, "chunks": chunk_count, "scenes": scene_count}

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        import json
        return json.loads(path.read_text(encoding="utf-8"))
