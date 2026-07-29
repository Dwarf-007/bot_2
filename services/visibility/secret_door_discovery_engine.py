from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from models.secret_discovery_models import DiscoveryCheckResult, SecretDiscoveryState
from services.visibility.secret_discovery_state_store import SecretDiscoveryStateStore


class SecretDoorDiscoveryEngine:
    """Secret door and hidden trait discovery engine.

    Works with:
    - corridor_visibility_graph.json
    - corridor_visibility_labels.json
    - visibility_state.json

    Core principles:
    - `secret` / `hidden` / `concealed` / `invisible` exits are filtered from player look until revealed.
    - `trapped` remains visible as the mundane object, but trap trait is hidden until revealed.
    - Discovery can be deterministic/manual or check-result based.
    """

    SECRET_TRAITS = {"secret"}
    HIDDEN_EXIT_TRAITS = {"secret"}
    TRAP_TRAITS = {"trapped"}

    def __init__(self, bundle_dir: str | Path, state_file: str | Path | None = None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.labels = self._read_json('corridor_visibility_labels.json')
        self.visibility_graph = self._read_json('corridor_visibility_graph.json')
        self.state_store = SecretDiscoveryStateStore(state_file or (self.bundle_dir / 'secret_discovery_state.json'))

    def init_state(self, campaign_id: str, scope_id: str = 'party', overwrite: bool = False) -> SecretDiscoveryState:
        return self.state_store.init(campaign_id=campaign_id, scope_id=scope_id, overwrite=overwrite)

    def load_or_init_state(self, campaign_id: str, scope_id: str = 'party') -> SecretDiscoveryState:
        state = self.state_store.load()
        if state:
            return state
        return self.init_state(campaign_id, scope_id)

    def filter_player_visible_exits(self, exits: List[Dict[str, Any]], state: SecretDiscoveryState) -> List[Dict[str, Any]]:
        """Filter visible exits for player-safe look.

        Secret exits are removed until their `secret` trait is revealed.
        Trap traits are not removed; only trap words/details are hidden by label policy.
        """
        result: List[Dict[str, Any]] = []
        for item in exits:
            sid = item.get('segment_id')
            traits = set(item.get('hidden_traits') or [])
            if sid:
                label = self.segment_label(sid)
                traits |= set(label.get('hidden_traits') or [])
            if sid and (traits & self.HIDDEN_EXIT_TRAITS) and not any(state.is_revealed(sid, t) for t in traits & self.HIDDEN_EXIT_TRAITS):
                continue
            result.append(self._apply_revealed_traits_to_exit(item, state))
        return result

    def filter_look(self, look: Dict[str, Any], state: SecretDiscoveryState) -> Dict[str, Any]:
        look = dict(look)
        if 'visible_exits' in look:
            look['visible_exits'] = self.filter_player_visible_exits(list(look.get('visible_exits') or []), state)
        return look

    def search_current_visibility(self, visibility_state: Dict[str, Any], state: SecretDiscoveryState, *, trait: str = 'secret', roll_total: Optional[int] = None, dc: int = 15, auto_success: bool = False, reason: str = 'search') -> DiscoveryCheckResult:
        visible_segments = self._candidate_segments_from_visibility_state(visibility_state)
        return self.search_segments(visible_segments, state, trait=trait, roll_total=roll_total, dc=dc, auto_success=auto_success, reason=reason)

    def search_room(self, room_id: str, state: SecretDiscoveryState, *, trait: str = 'secret', roll_total: Optional[int] = None, dc: int = 15, auto_success: bool = False, reason: str = 'search_room') -> DiscoveryCheckResult:
        room_exits = self.labels.get('room_exits', {}).get(room_id, [])
        segments = [x.get('segment_id') for x in room_exits if x.get('segment_id')]
        return self.search_segments(segments, state, trait=trait, roll_total=roll_total, dc=dc, auto_success=auto_success, reason=reason)

    def search_segments(self, segment_ids: Iterable[str], state: SecretDiscoveryState, *, trait: str = 'secret', roll_total: Optional[int] = None, dc: int = 15, auto_success: bool = False, reason: str = 'search') -> DiscoveryCheckResult:
        unique_segments = []
        for sid in segment_ids:
            if sid and sid not in unique_segments:
                unique_segments.append(sid)

        success = auto_success or (roll_total is not None and roll_total >= dc)
        candidates = [sid for sid in unique_segments if trait in set(self.segment_label(sid).get('hidden_traits') or [])]
        discovered: List[Dict[str, Any]] = []

        if success:
            for sid in candidates:
                state.reveal(sid, trait, reason=reason, details={'roll_total': roll_total, 'dc': dc, 'auto_success': auto_success})
                discovered.append(self._discovery_payload(sid, trait))
            self.state_store.save(state)

        if not candidates:
            return DiscoveryCheckResult(True, f'Nincs felfedezhető `{trait}` jellegű rejtett kijárat a vizsgált környezetben.', [], len(unique_segments), state)
        if success and discovered:
            return DiscoveryCheckResult(True, f'Sikeres keresés: {len(discovered)} rejtett elem felfedezve.', discovered, len(unique_segments), state)
        return DiscoveryCheckResult(False, f'Nem sikerült felfedezni rejtett `{trait}` elemet. DC {dc}, dobás: {roll_total}.', [], len(unique_segments), state)

    def reveal_segment(self, segment_id: str, state: SecretDiscoveryState, trait: str = 'secret', reason: str = 'manual') -> DiscoveryCheckResult:
        label = self.segment_label(segment_id)
        if not label:
            return DiscoveryCheckResult(False, f'Ismeretlen segment: {segment_id}', [], 0, state)
        state.reveal(segment_id, trait, reason=reason)
        self.state_store.save(state)
        return DiscoveryCheckResult(True, f'Felfedve: {segment_id} / {trait}', [self._discovery_payload(segment_id, trait)], 1, state)

    def segment_label(self, segment_id: str) -> Dict[str, Any]:
        return self.labels.get('segments', {}).get(segment_id, {})

    def secret_segments_for_room(self, room_id: str) -> List[Dict[str, Any]]:
        exits = self.labels.get('room_exits', {}).get(room_id, [])
        result = []
        for ex in exits:
            sid = ex.get('segment_id')
            label = self.segment_label(sid) if sid else {}
            traits = set(ex.get('hidden_traits') or []) | set(label.get('hidden_traits') or [])
            if traits & self.SECRET_TRAITS:
                result.append(ex)
        return result

    def _apply_revealed_traits_to_exit(self, item: Dict[str, Any], state: SecretDiscoveryState) -> Dict[str, Any]:
        item = dict(item)
        sid = item.get('segment_id')
        if not sid:
            return item
        revealed = state.revealed_segments.get(sid, [])
        item['revealed_traits'] = revealed
        if 'secret' in revealed:
            # Once discovered, make the player label explicit but still not overly mechanical.
            base = item.get('player_label') or item.get('label') or item.get('description') or sid
            if 'rejtett' not in base.lower():
                item['label'] = f'{base} (felfedezett rejtett átjáró)'
            item['description'] = item.get('description') or 'A korábban rejtett átjáró most már felismerhető.'
        if 'trapped' in revealed:
            item['label'] = item.get('label') or item.get('player_label') or sid
            item['description'] = (item.get('description') or '') + ' Gyanús mechanikus részletek vagy csapdára utaló nyomok láthatók.'
        return item

    def _candidate_segments_from_visibility_state(self, visibility_state: Dict[str, Any]) -> List[str]:
        current = visibility_state.get('current') or {}
        candidates: List[str] = []
        if current.get('segment_id'):
            candidates.append(current['segment_id'])
        for sid in visibility_state.get('visited_segments') or []:
            if sid not in candidates:
                candidates.append(sid)
        # Also use nearby visible segments if caller passed a look payload inside state.
        for sid in visibility_state.get('visible_segments') or []:
            if sid not in candidates:
                candidates.append(sid)
        # If player is in a room, use all room exits from labels.
        room_id = current.get('room_id')
        if room_id:
            for ex in self.labels.get('room_exits', {}).get(room_id, []):
                sid = ex.get('segment_id')
                if sid and sid not in candidates:
                    candidates.append(sid)
        return candidates

    def _discovery_payload(self, segment_id: str, trait: str) -> Dict[str, Any]:
        label = self.segment_label(segment_id)
        return {
            'segment_id': segment_id,
            'trait': trait,
            'player_label': label.get('player_label') or label.get('primary_label'),
            'dm_label': label.get('dm_label'),
            'target_room_ids': label.get('target_room_ids', []),
            'hidden_traits': label.get('hidden_traits', []),
        }

    def _read_json(self, name: str) -> Dict[str, Any]:
        path = self.bundle_dir / name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
