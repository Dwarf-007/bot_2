from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.visibility.player_look_sanitizer import PlayerLookSanitizer

try:
    from services.visibility.secret_door_discovery_engine import SecretDoorDiscoveryEngine
except Exception:
    SecretDoorDiscoveryEngine = None  # type: ignore


class VisibilityLabelService:
    """Loads corridor_visibility_labels.json and enriches/sanitizes player look payloads.

    Player mode:
    - only segment-based exits remain;
    - high-level room-to-room edges are removed;
    - target room IDs are stripped from labels;
    - DM-only fields are removed from player payload;
    - secret exits are filtered until discovered.

    DM mode can be enabled by constructing with mode='dm'.
    """

    def __init__(self, bundle_dir: str | Path, mode: str = 'player', discovery_state_file: str | Path | None = None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.mode = mode
        self.data = self._load()
        self.segment_labels = self.data.get('segments', {})
        self.room_exits = self.data.get('room_exits', {})
        self.sanitizer = PlayerLookSanitizer()
        self.discovery_engine = SecretDoorDiscoveryEngine(self.bundle_dir, discovery_state_file) if SecretDoorDiscoveryEngine is not None else None

    @property
    def available(self) -> bool:
        return bool(self.segment_labels)

    def label_for_segment(self, segment_id: str) -> Optional[Dict[str, Any]]:
        return self.segment_labels.get(segment_id)

    def exits_for_room(self, room_id: str) -> List[Dict[str, Any]]:
        return self.room_exits.get(room_id, [])

    def enrich_exit(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(item)
        sid = item.get('segment_id')
        if not sid:
            return item
        label = self.label_for_segment(sid)
        if not label:
            return item

        item['label'] = label.get('player_label') or label.get('primary_label') or item.get('description') or sid
        item['description'] = label.get('player_description') or label.get('primary_description') or item.get('description') or item['label']
        item['player_label'] = label.get('player_label') or item.get('label')
        item['player_description'] = label.get('player_description') or item.get('description')
        item['hidden_traits'] = label.get('hidden_traits', [])
        item['visible_traits'] = label.get('visible_traits', [])
        item['requires_detection'] = label.get('requires_detection', False)
        item['revealed_traits'] = []
        item['dm_label'] = label.get('dm_label')
        item['dm_description'] = label.get('dm_description')
        item['door_metadata'] = label.get('door_metadata', [])
        item['target_room_ids'] = label.get('target_room_ids', [])
        if not item.get('direction_hint') and label.get('directions'):
            item['direction_hint'] = label['directions'][0]
        return item

    def enrich_look(self, look: Dict[str, Any], campaign_id: str = 'campaign', scope_id: str = 'party') -> Dict[str, Any]:
        if not self.available:
            return self.sanitizer.sanitize_look(look, include_dm=self.mode == 'dm')

        look = dict(look)
        if 'visible_exits' in look:
            exits = [self.enrich_exit(x) for x in look.get('visible_exits', [])]
            if self.discovery_engine is not None:
                state = self.discovery_engine.load_or_init_state(campaign_id=campaign_id, scope_id=scope_id)
                exits = self.discovery_engine.filter_player_visible_exits(exits, state)
            look['visible_exits'] = exits
        return self.sanitizer.sanitize_look(look, include_dm=self.mode == 'dm')

    def _load(self) -> Dict[str, Any]:
        path = self.bundle_dir / 'corridor_visibility_labels.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
