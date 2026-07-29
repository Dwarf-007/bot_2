from __future__ import annotations
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from models.corridor_visibility_models import VisibilityPosition, VisibilitySegment, VisibilityState
from services.movement.navigation_repository import NavigationRepository
from services.visibility.donjon_visibility_grid import DonjonVisibilityGrid, Cell
from services.visibility.corridor_segmenter import CorridorSegmenter
from services.donjon.raw_donjon import extract_donjon_raw

class CorridorVisibilityEngine:
    """Cell/segment alapú láthatóság és folyosó-mozgás.

    MVP szabály:
    - szobában állva a szoba ismert kijáratai látszanak,
    - folyosón állva csak az aktuális segment + közvetlenül kapcsolódó junction/doorway segmentek látszanak,
    - kanyar/junction után levő további ajtók csak akkor látszanak, ha a játékos odalép.
    """

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.nav_repo = NavigationRepository(bundle_dir)
        self.visibility_graph = self._load_or_build_visibility_graph()

    def init_state(self, campaign_id: str, start_room_id: str) -> VisibilityState:
        rid = self.nav_repo.resolve_room_id(start_room_id) or start_room_id
        level = self._level_from_room_id(rid)
        state = VisibilityState(
            campaign_id=campaign_id,
            current=VisibilityPosition(node_id=rid, node_type='room', level=level, room_id=rid),
            visited_rooms=[rid],
        )
        self.refresh_visible(state)
        return state

    def look(self, state: VisibilityState) -> Dict[str, Any]:
        self.refresh_visible(state)
        if state.current.node_type == 'room':
            room = self.nav_repo.get_room(state.current.room_id or state.current.node_id)
            return {
                'position': state.current.to_dict(),
                'description': room.get('facts') if room else '',
                'visible_exits': self._room_visible_exits(state),
                'visible_cells_count': len(state.visible_cells),
            }
        seg = self._get_segment(state.current.segment_id or state.current.node_id)
        return {
            'position': state.current.to_dict(),
            'segment': seg.to_dict() if seg else None,
            'visible_segments': self._visible_segment_ids(state),
            'nearby_rooms': self._nearby_rooms_from_segment(seg) if seg else [],
            'visible_cells_count': len(state.visible_cells),
        }

    def move_to_segment(self, state: VisibilityState, segment_id: str) -> Dict[str, Any]:
        seg = self._get_segment(segment_id)
        if not seg:
            return {'ok': False, 'message': f'Unknown segment: {segment_id}', 'state': state.to_dict()}
        allowed = False
        if state.current.node_type == 'segment':
            cur = self._get_segment(state.current.segment_id or state.current.node_id)
            allowed = bool(cur and segment_id in cur.connected_segments)
        else:
            room_id = state.current.room_id or state.current.node_id
            allowed = room_id in seg.adjacent_rooms
        if not allowed:
            return {'ok': False, 'message': f'Segment not reachable from current position: {segment_id}', 'state': state.to_dict()}
        state.path_history.append(state.current.to_dict())
        state.current = VisibilityPosition(node_id=segment_id, node_type='segment', level=seg.level, segment_id=segment_id, cell=seg.cells[0] if seg.cells else None)
        if segment_id not in state.visited_segments:
            state.visited_segments.append(segment_id)
        self.refresh_visible(state)
        return {'ok': True, 'message': f'Beléptél a folyosószakaszra: {segment_id}', 'state': state.to_dict(), 'look': self.look(state)}

    def enter_room(self, state: VisibilityState, room_id: str) -> Dict[str, Any]:
        rid = self.nav_repo.resolve_room_id(room_id) or room_id
        if state.current.node_type == 'segment':
            seg = self._get_segment(state.current.segment_id or state.current.node_id)
            if not seg or rid not in seg.adjacent_rooms:
                return {'ok': False, 'message': f'A szoba nem innen nyílik: {rid}', 'state': state.to_dict()}
        state.path_history.append(state.current.to_dict())
        level = self._level_from_room_id(rid)
        state.current = VisibilityPosition(node_id=rid, node_type='room', level=level, room_id=rid)
        if rid not in state.visited_rooms:
            state.visited_rooms.append(rid)
        self.refresh_visible(state)
        return {'ok': True, 'message': f'Beléptél a szobába: {rid}', 'state': state.to_dict(), 'look': self.look(state)}

    def back(self, state: VisibilityState) -> Dict[str, Any]:
        if not state.path_history:
            return {'ok': False, 'message': 'Nincs előző pozíció.', 'state': state.to_dict()}
        prev = state.path_history.pop()
        state.current = VisibilityPosition(
            node_id=prev.get('node_id'), node_type=prev.get('node_type'), level=int(prev.get('level') or 1),
            room_id=prev.get('room_id'), segment_id=prev.get('segment_id'), cell=tuple(prev['cell']) if prev.get('cell') else None,
        )
        self.refresh_visible(state)
        return {'ok': True, 'message': 'Visszaléptél az előző pozícióra.', 'state': state.to_dict(), 'look': self.look(state)}

    def refresh_visible(self, state: VisibilityState) -> None:
        cells: Set[Cell] = set()
        if state.current.node_type == 'room':
            room = self.nav_repo.get_room(state.current.room_id or state.current.node_id) or {}
            for cell in self._room_bbox_cells(room):
                cells.add(cell)
            # reveal immediately adjacent doorway/segment cells, but not the whole corridor beyond junctions
            for seg in self._segments_for_room(state.current.room_id or state.current.node_id):
                cells.update(seg.cells[: min(len(seg.cells), 3)])
        else:
            for sid in self._visible_segment_ids(state):
                seg = self._get_segment(sid)
                if seg:
                    cells.update(seg.cells)
        state.visible_cells = sorted(cells)

    def _room_visible_exits(self, state: VisibilityState) -> List[Dict[str, Any]]:
        room_id = state.current.room_id or state.current.node_id
        exits = []
        for seg in self._segments_for_room(room_id):
            exits.append({'segment_id': seg.segment_id, 'segment_type': seg.segment_type, 'direction_hint': seg.direction_hint, 'description': f'Folyosó/ajtó: {seg.segment_id}'})
        # Also retain high-level room neighbors as DM hints, but mark hidden_beyond_corner.
        for opt in self.nav_repo.all_options(room_id).items():
            direction, items = opt
            for item in items if isinstance(items, list) else [items]:
                exits.append({'direction': direction, 'room_id': item.get('room_id'), 'edge_type': item.get('edge_type'), 'visible_now': item.get('edge_type') == 'door', 'description': item.get('description','')})
        return exits

    def _visible_segment_ids(self, state: VisibilityState) -> List[str]:
        if state.current.node_type != 'segment':
            return []
        sid = state.current.segment_id or state.current.node_id
        seg = self._get_segment(sid)
        if not seg:
            return []
        # Current segment and immediate neighbors only. This is the bend/junction visibility limiter.
        return [sid] + list(seg.connected_segments)

    def _nearby_rooms_from_segment(self, seg: VisibilitySegment) -> List[str]:
        rooms = list(seg.adjacent_rooms)
        # include rooms from directly adjacent doorway/junction segments
        for sid in seg.connected_segments:
            s2 = self._get_segment(sid)
            if s2:
                for rid in s2.adjacent_rooms:
                    if rid not in rooms:
                        rooms.append(rid)
        return rooms

    def _load_or_build_visibility_graph(self) -> Dict[str, Any]:
        path = self.bundle_dir / 'corridor_visibility_graph.json'
        if path.exists():
            import json
            return json.loads(path.read_text(encoding='utf-8'))
        from services.visibility.visibility_graph_builder import VisibilityGraphBuilder
        return VisibilityGraphBuilder(self.bundle_dir).build_and_save()

    def _get_segment(self, segment_id: str) -> Optional[VisibilitySegment]:
        raw = self.visibility_graph.get('segments', {}).get(segment_id)
        if not raw: return None
        return VisibilitySegment(
            segment_id=raw['segment_id'], level=int(raw['level']), segment_type=raw['segment_type'],
            cells=[tuple(x) for x in raw.get('cells', [])], endpoints=[tuple(x) for x in raw.get('endpoints', [])],
            connected_segments=list(raw.get('connected_segments') or []), adjacent_rooms=list(raw.get('adjacent_rooms') or []),
            direction_hint=raw.get('direction_hint'),
        )

    def _segments_for_room(self, room_id: str) -> List[VisibilitySegment]:
        ids = self.visibility_graph.get('room_to_segments', {}).get(room_id, [])
        return [s for sid in ids if (s := self._get_segment(sid))]

    def init_state_in_corridor(self, campaign_id: str, segment_id: str, row: int, col: int) -> VisibilityState:
        state = VisibilityState(
            campaign_id=campaign_id,
            current=VisibilityPosition(
                node_id=segment_id,
                node_type='segment',
                level=self._level_from_segment(segment_id),
                segment_id=segment_id,
                cell=(row, col),
            ),
            visited_segments=[segment_id],
        )
        self.refresh_visible(state)
        return state

    def _level_from_segment(self, segment_id: str) -> int:
        import re
        m = re.search(r':L(\d+):', segment_id)
        return int(m.group(1)) if m else 1

    @staticmethod
    def _level_from_room_id(room_id: str) -> int:
        import re
        m = re.search(r':L(\d+):', room_id or '')
        return int(m.group(1)) if m else 1

    @staticmethod
    def _room_bbox_cells(room: Dict[str, Any]) -> List[Cell]:
        raw = extract_donjon_raw(room)
        west = int(raw.get('west') or raw.get('col') or 0)
        east = int(raw.get('east') or west)
        north = int(raw.get('north') or raw.get('row') or 0)
        south = int(raw.get('south') or north)
        return [(r, c) for r in range(north, south + 1) for c in range(west, east + 1)]
