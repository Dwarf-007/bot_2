from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.movement.navigation_repository import NavigationRepository
from services.visibility.donjon_visibility_grid import DonjonVisibilityGrid
from services.visibility.corridor_segment_merge_engine import CorridorSegmentMergeEngine, room_boxes_from_room_data


class VisibilityGraphBuilder:
    """Corridor Visibility Graph Builder v2 — Segment Merge Engine.

    A v1/v0 visibility graph túl sok mikroszegmenst készített, mert room interior floor cellákat is
    segmentált. Ez a builder a room bboxok alapján maszkolja a szobabelsőt, és hallway-level segmenteket
    készít.
    """

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.repo = NavigationRepository(bundle_dir)

    def build_and_save(self) -> Dict[str, Any]:
        graph = self.build()
        out = self.bundle_dir / 'corridor_visibility_graph.json'
        out.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
        return graph

    def build(self) -> Dict[str, Any]:
        levels = self._levels()
        all_segments: Dict[str, Dict[str, Any]] = {}
        room_to_segments: Dict[str, List[str]] = {}
        reports: List[Dict[str, Any]] = []

        for info in levels:
            level = int(info.get('level') or info.get('level_number') or 1)
            tsv_file = info.get('tsv_file') or self._find_tsv_for_level(level)
            if not tsv_file or not Path(tsv_file).exists():
                reports.append({'level': level, 'warning': 'missing_tsv'})
                continue

            grid = DonjonVisibilityGrid.from_tsv(tsv_file)
            prefix = f'{self._campaign_id()}:L{level:02d}'
            boxes = room_boxes_from_room_data(self.repo.room_data, level)
            built = CorridorSegmentMergeEngine(grid, level, prefix, boxes).build()

            segments = built['segments']
            for sid, seg in segments.items():
                all_segments[sid] = seg.to_dict()
            for rid, sids in built['room_to_segments'].items():
                room_to_segments.setdefault(rid, [])
                for sid in sids:
                    if sid not in room_to_segments[rid]:
                        room_to_segments[rid].append(sid)

            reports.append({
                'level': level,
                'tsv_file': str(tsv_file),
                'room_boxes': len(boxes),
                'tokens': grid.token_summary(),
                **built['stats'],
            })

        return {
            'schema_version': 'corridor_visibility_graph.v2',
            'campaign_id': self._campaign_id(),
            'segments': all_segments,
            'room_to_segments': room_to_segments,
            'reports': reports,
        }

    def _levels(self) -> List[Dict[str, Any]]:
        fog = self._read_json('fog_manifest.json')
        levels = fog.get('levels') or []
        if levels:
            return levels
        graph = self._read_json('dungeon_graph.json')
        return graph.get('levels') or []

    def _find_tsv_for_level(self, level: int) -> Optional[str]:
        candidates = []
        for p in self.bundle_dir.rglob('*.tsv'):
            name = p.name.lower()
            score = 0
            if f'l{level:02d}' in name:
                score += 10
            if f'level_{level:02d}' in str(p).lower():
                score += 5
            if score:
                candidates.append((score, p))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], str(x[1])))
        return str(candidates[0][1])

    def _read_json(self, name: str) -> Dict[str, Any]:
        p = self.bundle_dir / name
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

    def _campaign_id(self) -> str:
        graph = self._read_json('dungeon_graph.json')
        return graph.get('campaign_id') or 'campaign'
