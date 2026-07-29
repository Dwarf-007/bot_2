
"""
SERVICES/CONTEXT_SERVICE.PY
Campaign context aggregation with progress summary injection.
"""

from __future__ import annotations

from typing import Any, Dict


class ContextService:
    def __init__(self, channel_repo, location_repo=None, rag_runtime=None, memory_repo=None, memory_summary_service=None, progress_service=None) -> None:
        self.channel_repo = channel_repo
        self.location_repo = location_repo
        self.rag_runtime = rag_runtime
        self.memory_repo = memory_repo
        self.memory_summary_service = memory_summary_service
        self.progress_service = progress_service

    def get_context(self, channel_id: str, player_id: str, player_message: str) -> Dict[str, Any]:
        state = self.channel_repo.get_state(channel_id)
        room_id = state.get("current_location_id")
        room = self.location_repo.get_room(room_id) if self.location_repo and room_id else None
        campaign_id = self._campaign_id_from_state_or_room(state, room)

        rag_chunks = []
        if self.rag_runtime and str(state.get("mode", "campaign")).lower() == "campaign":
            try:
                rag_chunks = self.rag_runtime.search(player_message, top_k=5, campaign_id=campaign_id, room_id=room_id)
            except TypeError:
                rag_chunks = self.rag_runtime.search(player_message, top_k=5)
            except Exception:
                rag_chunks = []

        summary_parts = []
        if self.memory_repo and self.memory_summary_service:
            try:
                summary_parts.append(self.memory_summary_service.build_recent_summary(self.memory_repo.list_recent_events(channel_id, limit=20)))
            except Exception:
                pass
        if self.progress_service:
            try:
                summary_parts.append(self.progress_service.progress_text(channel_id))
            except Exception:
                pass

        return {
            "campaign_id": campaign_id,
            "room_facts": room.get("facts", "") if room else "",
            "room_exits": room.get("exits", {}) if room else {},
            "summary_text": "\n".join(part for part in summary_parts if part),
            "messages": state.get("context_window", []),
            "player": str(player_id),
            "active_player": state.get("active_player"),
            "mode": state.get("mode", "campaign"),
            "style": state.get("style", "grimdark"),
            "difficulty": state.get("difficulty", "standard"),
            "current_state": state.get("current_state", "EXPLORATION"),
            "current_location_id": room_id,
            "rag_chunks": rag_chunks,
        }

    @staticmethod
    def _campaign_id_from_state_or_room(state: Dict[str, Any], room: Dict[str, Any] | None) -> str:
        if state.get("campaign_id"):
            return str(state["campaign_id"])
        if room and room.get("campaign_id"):
            return str(room["campaign_id"])
        return "default"
