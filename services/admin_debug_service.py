
"""
SERVICES/ADMIN_DEBUG_SERVICE.PY
Admin/debug helper service with progress and runtime health commands.
"""

from __future__ import annotations


class AdminDebugService:
    def __init__(self, channel_repo, party_repo, player_repo=None, inventory_repo=None, location_repo=None, memory_repo=None, memory_summary_service=None, combat_repo=None, rag_runtime=None, campaign_service=None, room_alias_service=None, progress_service=None, runtime_health_service=None) -> None:
        self.channel_repo = channel_repo
        self.party_repo = party_repo
        self.player_repo = player_repo
        self.inventory_repo = inventory_repo
        self.location_repo = location_repo
        self.memory_repo = memory_repo
        self.memory_summary_service = memory_summary_service
        self.combat_repo = combat_repo
        self.rag_runtime = rag_runtime
        self.campaign_service = campaign_service
        self.room_alias_service = room_alias_service
        self.progress_service = progress_service
        self.runtime_health_service = runtime_health_service

    def _active_campaign_id(self, channel_id: str) -> str:
        if self.campaign_service:
            return self.campaign_service.get_active_campaign_id(channel_id)
        state = self.channel_repo.get_state(channel_id)
        return str(state.get("campaign_id") or "default")

    def health_text(self, channel_id: str | None = None) -> str:
        if not self.runtime_health_service:
            return "RuntimeHealthService nincs bekötve."
        campaign_id = self._active_campaign_id(channel_id) if channel_id else "default"
        return self.runtime_health_service.run_all(campaign_id=campaign_id, channel_id=channel_id).to_text()

    def progress_text(self, channel_id: str) -> str:
        return self.progress_service.progress_text(channel_id) if self.progress_service else "ProgressService nincs bekötve."

    def scene_list_text(self, channel_id: str) -> str:
        return self.progress_service.scene_list_text(channel_id) if self.progress_service else "ProgressService nincs bekötve."

    def scene_set_text(self, channel_id: str, scene_id: str) -> str:
        return self.progress_service.set_scene(channel_id, scene_id) if self.progress_service else "ProgressService nincs bekötve."

    def objective_add_text(self, channel_id: str, text: str) -> str:
        return self.progress_service.add_objective(channel_id, text) if self.progress_service else "ProgressService nincs bekötve."

    def objective_done_text(self, objective_id: int) -> str:
        return self.progress_service.complete_objective(objective_id) if self.progress_service else "ProgressService nincs bekötve."

    def state_text(self, channel_id: str) -> str:
        state = self.channel_repo.get_state(channel_id)
        combat_text = ""
        if self.combat_repo:
            combat = self.combat_repo.get_combat_state(channel_id)
            combat_text = f"\n**Combat:** {'active' if combat.active else 'inactive'}\n**Combat room:** {combat.room_id}"
        return f"**AI DM channel state**\n**Channel:** `{channel_id}`\n**Campaign:** `{state.get('campaign_id', 'default')}`\n**State:** `{state.get('current_state')}`\n**Location:** `{state.get('current_location_id')}`\n**Mode:** `{state.get('mode')}`\n**Style:** `{state.get('style')}`\n**Difficulty:** `{state.get('difficulty')}`{combat_text}"

    def set_room(self, channel_id: str, room_value: str) -> str:
        value = str(room_value or "").strip()
        if not value:
            return "Hiányzó room_id vagy room alias."
        campaign_id = self._active_campaign_id(channel_id)
        room_id = value
        if self.room_alias_service:
            room_id = self.room_alias_service.resolve_room_id(campaign_id, value) or value
        if self.location_repo and not self.location_repo.get_room(room_id):
            return f"Nem található ilyen szoba/helyszín vagy alias: `{room_value}`"
        self.channel_repo.set_location(channel_id, room_id)
        return f"Aktuális helyszín beállítva: `{room_id}`"

    def find_room_text(self, channel_id: str, query: str, limit: int = 10) -> str:
        return self.room_alias_service.find_text(self._active_campaign_id(channel_id), query, limit=limit) if self.room_alias_service else "RoomAliasService nincs bekötve."

    def campaign_set_text(self, channel_id: str, campaign_id: str) -> str:
        return self.campaign_service.set_active_campaign(channel_id, campaign_id) if self.campaign_service else "CampaignService nincs bekötve."

    def campaign_status_text(self, channel_id: str) -> str:
        return self.campaign_service.status_text(channel_id) if self.campaign_service else "CampaignService nincs bekötve."

    def campaign_list_text(self) -> str:
        return self.campaign_service.list_campaigns_text() if self.campaign_service else "CampaignService nincs bekötve."

    def set_mode(self, channel_id: str, mode: str) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized not in {"campaign", "freeplay"}:
            return "Érvénytelen mód. Használható: `campaign` vagy `freeplay`."
        self.channel_repo.set_mode(channel_id, normalized)
        return f"Mód beállítva: `{normalized}`"

    def set_style(self, channel_id: str, style: str) -> str:
        value = str(style or "").strip()
        if not value:
            return "Hiányzó style érték."
        self.channel_repo.set_style(channel_id, value)
        return f"Stílus beállítva: `{value}`"

    def set_difficulty(self, channel_id: str, difficulty: str) -> str:
        value = str(difficulty or "").strip().lower()
        if not value:
            return "Hiányzó difficulty érték."
        self.channel_repo.set_difficulty(channel_id, value)
        return f"Nehézség beállítva: `{value}`"

    def party_text(self, channel_id: str) -> str:
        party = self.party_repo.get_party_members(channel_id)
        return "Nincs regisztrált party ebben a csatornában." if not party else "\n".join(["**Party tagok:**"] + [f"- <@{pid}>" for pid in party])

    def inventory_text(self, channel_id: str, player_id: str) -> str:
        if not self.inventory_repo:
            return "InventoryRepository nincs bekötve."
        inv = self.inventory_repo.get_inventory(channel_id, player_id)
        return f"**Inventory — <@{player_id}>**\nGold: `{inv.get('gold', 0.0)}`\nItems: `{inv.get('items', {})}`\nAmmo: `{inv.get('ammo', {})}`"

    def recent_memory_text(self, channel_id: str, limit: int = 10) -> str:
        if not self.memory_repo:
            return "MemoryRepository nincs bekötve."
        events = self.memory_repo.list_recent_events(channel_id, limit=limit)
        if not events:
            return "Nincs mentett memory event ebben a csatornában."
        if self.memory_summary_service:
            summary = self.memory_summary_service.build_recent_summary(events, max_lines=limit)
            if summary:
                return f"**Recent memory summary:**\n{summary}"
        return "\n".join(f"- `{event.id}` `{event.event_type}` {event.data}" for event in events)

    def clear_memory(self, channel_id: str) -> str:
        if not self.memory_repo:
            return "MemoryRepository nincs bekötve."
        self.memory_repo.clear_channel_memory(channel_id)
        return "A csatorna memory eventjei törölve."

    def exit_channel_text(self, channel_id: str) -> str:
        self.channel_repo.reset_state(channel_id)
        clear_combat = getattr(self.combat_repo, "clear_combat_state", None)
        if clear_combat:
            try:
                clear_combat(channel_id)
            except Exception:
                pass
        return (
            "A csatorna kilépett az aktív kampányból, és visszatért a kiválasztó (alapértelmezett) állapotba. "
            "Használd a `!dm_campaign_list` és `!dm_campaign_set <id>` parancsokat egy új kampány indításához."
        )

    def room_text(self, room_value: str, channel_id: str | None = None) -> str:
        if not self.location_repo:
            return "LocationRepository nincs bekötve."
        room_id = str(room_value or "").strip()
        if channel_id and self.room_alias_service:
            room_id = self.room_alias_service.resolve_room_id(self._active_campaign_id(channel_id), room_value) or room_id
        room = self.location_repo.get_room(room_id)
        if not room:
            return f"Nem található room: `{room_value}`"
        return f"**Room:** `{room.get('room_id')}`\n**Title:** {room.get('title')}\n**Campaign:** `{room.get('campaign_id', 'default')}`\n**Facts:**\n{str(room.get('facts') or '')[:1500]}"

    def rag_search_text(self, query: str, campaign_id: str = "default", limit: int = 5) -> str:
        if not self.rag_runtime:
            return "RAG runtime nincs bekötve."
        results = self.rag_runtime.search(query, top_k=limit, campaign_id=campaign_id)
        if not results:
            return "Nincs releváns RAG találat."
        return "\n".join([f"**RAG találatok — campaign `{campaign_id}`:**"] + [f"- `{item.get('chunk_id')}` score=`{item.get('score')}` room=`{item.get('room_id')}`\n{str(item.get('text') or '').replace(chr(10), ' ')[:350]}" for item in results])
