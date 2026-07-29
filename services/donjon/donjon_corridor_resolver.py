from __future__ import annotations
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from models.dungeon_graph_models import DungeonEdge, DungeonRoom
from services.donjon.donjon_tsv_parser import DonjonTsvMap, DonjonTsvParser

@dataclass
class CorridorRegion:
    region_id: str
    level: int
    cells: List[Tuple[int, int]]
    touched_rooms: List[str]
    touched_doors: List[Dict[str, Any]]
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class UnresolvedDoor:
    room_id: str
    level: int
    room_number: int
    direction: str
    row: Optional[int]
    col: Optional[int]
    description: str
    reason: str
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

class DonjonCorridorResolver:
    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id

    def resolve_level(self, level: int, tsv_file: str | Path, rooms: List[DungeonRoom]) -> Dict[str, Any]:
        grid = DonjonTsvParser.parse_file(tsv_file)
        room_by_id = {r.room_id: r for r in rooms if r.level == level}
        cell_to_rooms = self._build_room_cell_index(list(room_by_id.values()))
        regions = self._corridor_regions(level, grid, cell_to_rooms)
        edges, unresolved = self._edges_from_regions(level, regions, room_by_id)
        return {
            'level': level,
            'tsv_file': str(tsv_file),
            'token_summary': DonjonTsvParser.token_summary(grid),
            'regions': [r.to_dict() for r in regions],
            'edges': [e.to_dict() for e in edges],
            'unresolved_doors': [u.to_dict() for u in unresolved],
        }

    def _build_room_cell_index(self, rooms: List[DungeonRoom]) -> Dict[Tuple[int, int], Set[str]]:
        idx: Dict[Tuple[int,int], Set[str]] = defaultdict(set)
        for room in rooms:
            if None in (room.north, room.south, room.west, room.east):
                continue
            for r in range(int(room.north), int(room.south)+1):
                for c in range(int(room.west), int(room.east)+1):
                    idx[(r,c)].add(room.room_id)
        return idx

    def _corridor_regions(self, level: int, grid: DonjonTsvMap, cell_to_rooms: Dict[Tuple[int,int], Set[str]]) -> List[CorridorRegion]:
        seen: Set[Tuple[int,int]] = set()
        regions: List[CorridorRegion] = []
        for row in grid.cells:
            for cell in row:
                pos = (cell.row, cell.col)
                if pos in seen or not cell.walkable:
                    continue
                # Start only outside room interiors; room cells are not known from TSV, so exclude cells inside room bbox index.
                if pos in cell_to_rooms and not cell.door_like and not cell.stair:
                    continue
                q = deque([cell])
                seen.add(pos)
                cells: List[Tuple[int,int]] = []
                touched_rooms: Set[str] = set()
                touched_doors: List[Dict[str, Any]] = []
                while q:
                    cur = q.popleft()
                    cells.append((cur.row, cur.col))
                    # rooms around this cell, not only at this exact coordinate
                    for rr in range(cur.row-1, cur.row+2):
                        for cc in range(cur.col-1, cur.col+2):
                            touched_rooms.update(cell_to_rooms.get((rr,cc), set()))
                    if cur.door_like or cur.stair:
                        touched_doors.append({'row': cur.row, 'col': cur.col, 'token': cur.token, 'kind': cur.kind, 'stair': cur.stair})
                    for nxt in grid.walkable_neighbors4(cur.row, cur.col):
                        npos = (nxt.row, nxt.col)
                        if npos in seen:
                            continue
                        # don't flood deep into room boxes unless the token is a door/stair marker
                        if npos in cell_to_rooms and not nxt.door_like and not nxt.stair:
                            continue
                        seen.add(npos)
                        q.append(nxt)
                if touched_rooms or touched_doors:
                    regions.append(CorridorRegion(f'L{level:02d}:C{len(regions)+1:04d}', level, cells, sorted(touched_rooms), touched_doors))
        return regions

    def _edges_from_regions(self, level: int, regions: List[CorridorRegion], room_by_id: Dict[str, DungeonRoom]) -> Tuple[List[DungeonEdge], List[UnresolvedDoor]]:
        edges: List[DungeonEdge] = []
        unresolved: List[UnresolvedDoor] = []
        existing_pairs = set()
        for region in regions:
            rooms = region.touched_rooms
            if len(rooms) >= 2:
                for src in rooms:
                    for dst in rooms:
                        if src == dst:
                            continue
                        key = (src, dst, region.region_id)
                        if key in existing_pairs:
                            continue
                        existing_pairs.add(key)
                        src_room = room_by_id.get(src)
                        dst_room = room_by_id.get(dst)
                        if not src_room or not dst_room:
                            continue
                        direction = self._approx_direction(src_room, dst_room)
                        edges.append(DungeonEdge(
                            edge_id=f'{src}->{dst}:corridor:{region.region_id}',
                            from_room_id=src,
                            to_room_id=dst,
                            level_from=level,
                            level_to=level,
                            edge_type='corridor',
                            direction=direction,
                            reverse_direction=None,
                            door_type='corridor',
                            description=f'Corridor-resolved connection via {region.region_id}.',
                            confidence='tsv_corridor_region',
                            raw={'region_id': region.region_id, 'touched_doors': region.touched_doors},
                        ))
            elif len(rooms) == 1 and region.touched_doors:
                room = room_by_id.get(rooms[0])
                if room:
                    for d in region.touched_doors:
                        unresolved.append(UnresolvedDoor(room.room_id, level, room.room_number, 'unknown', d.get('row'), d.get('col'), f"TSV token {d.get('token')}", 'corridor_region_touches_only_one_room'))
        return edges, unresolved

    @staticmethod
    def _approx_direction(src: DungeonRoom, dst: DungeonRoom) -> Optional[str]:
        sr = ((src.north or src.row or 0) + (src.south or src.row or 0)) / 2
        sc = ((src.west or src.col or 0) + (src.east or src.col or 0)) / 2
        dr = ((dst.north or dst.row or 0) + (dst.south or dst.row or 0)) / 2
        dc = ((dst.west or dst.col or 0) + (dst.east or dst.col or 0)) / 2
        if abs(dr - sr) > abs(dc - sc):
            return 'south' if dr > sr else 'north'
        return 'east' if dc > sc else 'west'
