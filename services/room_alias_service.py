
"""
SERVICES/ROOM_ALIAS_SERVICE.PY
Application service for campaign-scoped room alias lookup.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class RoomAliasService:
    def __init__(self, alias_repo, location_repo=None) -> None:
        self.alias_repo = alias_repo
        self.location_repo = location_repo
        self.alias_repo.ensure_schema()

    def import_lookup(self, campaign_id: str, lookup: Dict[str, Any], source: str = "room_lookup.json") -> int:
        return self.alias_repo.import_lookup(campaign_id, lookup, source=source)

    def ensure_room_aliases_from_room(self, campaign_id: str, room: Dict[str, Any]) -> None:
        room_id = str(room.get("room_id") or "").strip()
        if not room_id:
            return
        title = str(room.get("title") or "").strip() or None
        slug = str(room.get("room_slug") or room.get("slug") or "").strip()
        self.alias_repo.upsert_alias(campaign_id, room_id, room_id, title=title, source="room_id")
        if title:
            self.alias_repo.upsert_alias(campaign_id, title, room_id, title=title, source="room_title")
        if slug:
            self.alias_repo.upsert_alias(campaign_id, slug, room_id, title=title, source="room_slug")

    def resolve_room_id(self, campaign_id: str, value: str) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        if self.location_repo and self.location_repo.get_room(text):
            return text
        record = self.alias_repo.resolve(campaign_id, text)
        if record:
            return record.room_id
        matches = self.alias_repo.search(campaign_id, text, limit=1)
        return matches[0].room_id if matches else None

    def find_text(self, campaign_id: str, query: str, limit: int = 10) -> str:
        matches = self.alias_repo.search(campaign_id, query, limit=limit)
        if not matches:
            return "Nincs room alias találat."
        lines = [f"**Room alias találatok — campaign `{campaign_id}`:**"]
        for item in matches:
            lines.append(f"- `{item.alias}` → `{item.room_id}` ({item.title or '-'}) source=`{item.source}`")
        return "\n".join(lines)
