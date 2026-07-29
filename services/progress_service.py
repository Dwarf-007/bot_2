
"""
SERVICES/PROGRESS_SERVICE.PY
Application service for scene progression and objectives.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


class ProgressService:
    def __init__(self, progress_repo, channel_repo, campaign_service=None, location_repo=None) -> None:
        self.progress_repo = progress_repo
        self.channel_repo = channel_repo
        self.campaign_service = campaign_service
        self.location_repo = location_repo
        self.progress_repo.ensure_schema()

    def active_campaign_id(self, channel_id: str) -> str:
        if self.campaign_service:
            return self.campaign_service.get_active_campaign_id(channel_id)
        state = self.channel_repo.get_state(channel_id)
        return str(state.get("campaign_id") or "default")

    def import_toc_entries(self, campaign_id: str, toc_data: Dict[str, Any]) -> int:
        entries = toc_data.get("entries", []) if isinstance(toc_data, dict) else []
        count = 0
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or entry.get("name") or f"Scene {index}")
            scene_id = str(entry.get("scene_id") or self._slug(title) or f"scene_{index}")
            self.progress_repo.upsert_scene(
                {
                    "campaign_id": campaign_id,
                    "scene_id": scene_id,
                    "title": title,
                    "order_index": int(entry.get("order_index", index) or index),
                    "room_id": entry.get("room_id"),
                    "source": entry.get("source"),
                    "metadata": entry,
                }
            )
            count += 1
        return count

    def ensure_scenes_from_rooms(self, campaign_id: str, rooms: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for index, room in enumerate(rooms or [], start=1):
            room_id = str(room.get("room_id") or "").strip()
            if not room_id:
                continue
            title = str(room.get("title") or room_id)
            scene_id = self._slug(title) or room_id
            self.progress_repo.upsert_scene(
                {
                    "campaign_id": campaign_id,
                    "scene_id": scene_id,
                    "title": title,
                    "order_index": index,
                    "room_id": room_id,
                    "source": "room_data",
                    "metadata": {"source_chunk_ids": room.get("source_chunk_ids", [])},
                }
            )
            count += 1
        return count

    def set_scene(self, channel_id: str, scene_id: str) -> str:
        campaign_id = self.active_campaign_id(channel_id)
        scene = self.progress_repo.get_scene(campaign_id, scene_id)
        if not scene:
            return f"Nem található scene `{scene_id}` a(z) `{campaign_id}` kampányban."
        self.progress_repo.set_channel_progress(
            channel_id=channel_id,
            campaign_id=campaign_id,
            current_scene_id=scene.scene_id,
            current_room_id=scene.room_id,
            milestone=scene.title,
            metadata={"source": "manual_scene_set"},
        )
        if scene.room_id:
            self.channel_repo.set_location(channel_id, scene.room_id)
        return f"Aktuális scene beállítva: `{scene.scene_id}` — {scene.title}"

    def scene_list_text(self, channel_id: str) -> str:
        campaign_id = self.active_campaign_id(channel_id)
        scenes = self.progress_repo.list_scenes(campaign_id)
        if not scenes:
            return f"Nincs scene bejegyzés a(z) `{campaign_id}` kampányhoz."
        lines = [f"**Scenes — campaign `{campaign_id}`:**"]
        for scene in scenes[:80]:
            room_part = f" room=`{scene.room_id}`" if scene.room_id else ""
            lines.append(f"- `{scene.scene_id}` #{scene.order_index} — {scene.title}{room_part}")
        return "\n".join(lines)

    def progress_text(self, channel_id: str) -> str:
        campaign_id = self.active_campaign_id(channel_id)
        progress = self.progress_repo.get_channel_progress(channel_id)
        objectives = self.progress_repo.list_objectives(channel_id, include_done=False, limit=20)
        lines = ["**Campaign progress**", f"Campaign: `{campaign_id}`"]
        if progress:
            lines.extend(
                [
                    f"Current scene: `{progress.current_scene_id}`",
                    f"Current room: `{progress.current_room_id}`",
                    f"Milestone: {progress.milestone or '-'}",
                ]
            )
        else:
            lines.append("Current scene: `-`")
        if objectives:
            lines.append("**Open objectives:**")
            for obj in objectives:
                lines.append(f"- `#{obj.objective_id}` {obj.text}")
        else:
            lines.append("Open objectives: `none`")
        return "\n".join(lines)

    def add_objective(self, channel_id: str, text: str) -> str:
        campaign_id = self.active_campaign_id(channel_id)
        state = self.channel_repo.get_state(channel_id)
        progress = self.progress_repo.get_channel_progress(channel_id)
        objective_id = self.progress_repo.add_objective(
            channel_id=channel_id,
            campaign_id=campaign_id,
            text=text,
            scene_id=progress.current_scene_id if progress else None,
            room_id=state.get("current_location_id"),
        )
        return f"Objective hozzáadva: `#{objective_id}` {text}"

    def complete_objective(self, objective_id: int) -> str:
        self.progress_repo.set_objective_status(int(objective_id), "DONE")
        return f"Objective lezárva: `#{objective_id}`"

    def cancel_objective(self, objective_id: int) -> str:
        self.progress_repo.set_objective_status(int(objective_id), "CANCELLED")
        return f"Objective törölve/lezárva: `#{objective_id}`"

    @staticmethod
    def _slug(value: str) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[^0-9a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+", "_", text)
        text = text.strip("_")
        return text[:80]
