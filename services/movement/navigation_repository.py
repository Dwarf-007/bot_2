from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

class NavigationRepository:
    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.navigation_index = self._read_json('navigation_index.json').get('rooms', {})
        self.room_data = {room['room_id']: room for room in self._read_json('room_data.json').get('rooms', [])}
        self.room_lookup = self._read_json('room_lookup.json')
        graph_path = self.bundle_dir / 'dungeon_graph.json'
        self.graph = self._read_json('dungeon_graph.json') if graph_path.exists() else {'edges': []}

    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        rid = self.resolve_room_id(room_id)
        return self.room_data.get(rid) if rid else None

    def resolve_room_id(self, value: str) -> Optional[str]:
        value = str(value or '').strip()
        if not value:
            return None
        if value in self.room_data:
            return value
        if value in self.room_lookup:
            return self.room_lookup[value]
        lowered = value.lower()
        for key, rid in self.room_lookup.items():
            if str(key).lower() == lowered:
                return rid
        return None

    def get_nav_entry(self, room_id: str) -> Optional[Dict[str, Any]]:
        rid = self.resolve_room_id(room_id)
        return self.navigation_index.get(rid) if rid else None

    def all_options(self, room_id: str) -> Dict[str, List[Dict[str, Any]]]:
        entry = self.get_nav_entry(room_id)
        return entry.get('neighbors', {}) if entry else {}

    def _read_json(self, file_name: str) -> Dict[str, Any]:
        path = self.bundle_dir / file_name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def normalize_direction(direction: str) -> str:
        mapping = {
            "north": "north", "n": "north",
            "south": "south", "s": "south",
            "east": "east", "e": "east",
            "west": "west", "w": "west",
            "up": "up", "u": "up",
            "down": "down", "d": "down",
            "észak": "north", "dél": "south", "kelet": "east", "nyugat": "west",
            "fel": "up", "le": "down",
        }
        return mapping.get(direction.lower().strip(), direction.lower().strip())
