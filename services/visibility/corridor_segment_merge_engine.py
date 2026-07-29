from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from models.corridor_visibility_models import VisibilitySegment
from services.visibility.donjon_visibility_grid import DonjonVisibilityGrid
from services.donjon.raw_donjon import extract_donjon_raw

Cell = Tuple[int, int]
BBox = Tuple[int, int, int, int]  # west, east, north, south


@dataclass
class RoomBox:
    room_id: str
    level: int
    west: int
    east: int
    north: int
    south: int

    def contains(self, cell: Cell) -> bool:
        r, c = cell
        return self.north <= r <= self.south and self.west <= c <= self.east

    def touches(self, cell: Cell, margin: int = 1) -> bool:
        r, c = cell
        return self.north - margin <= r <= self.south + margin and self.west - margin <= c <= self.east + margin


class CorridorSegmentMergeEngine:
    """Hallway-level segment builder a mikroszegmens-probléma ellen.

    A korábbi CorridorSegmenter sok mapon azért gyártott több ezer segmentet, mert a Donjon TSV
    `F` cellái a szobabelsőket is tartalmazzák. Ez a v2 engine először maszkolja a room bboxokon
    belüli cellákat, majd csak a tényleges folyosó/ajtó/lépcső cellákból épít hallway-level gráfot.

    Eredmény:
    - kevesebb, hosszabb corridor_segment,
    - külön doorway/stair/dead_end/junction node-ok,
    - room_to_segments kapcsolat a tényleges szobahatárhoz közeli segmentekhez.
    """

    WALK_MARGIN_TO_ROOM = 1

    def __init__(self, grid: DonjonVisibilityGrid, level: int, level_prefix: str, room_boxes: List[RoomBox]) -> None:
        self.grid = grid
        self.level = level
        self.level_prefix = level_prefix
        self.room_boxes = room_boxes
        self.segments: Dict[str, VisibilitySegment] = {}
        self.cell_to_segment: Dict[Cell, str] = {}
        self._counter = 1

    def build(self) -> Dict[str, Any]:
        walkable = self._corridor_walkable_cells()
        boundary = self._boundary_cells(walkable)

        # Explicit boundary nodes first.
        for cell in sorted(boundary):
            self._create_boundary_segment(cell, walkable)

        visited_edges: Set[Tuple[Cell, Cell]] = set()

        def edge_key(a: Cell, b: Cell) -> Tuple[Cell, Cell]:
            return tuple(sorted((a, b)))  # type: ignore[return-value]

        # Build chains between boundary nodes through degree-2 corridor cells.
        for start in sorted(boundary):
            for nb in self._walkable_neighbors(start, walkable):
                ekey = edge_key(start, nb)
                if ekey in visited_edges:
                    continue
                visited_edges.add(ekey)

                if nb in boundary:
                    self._connect(self.cell_to_segment.get(start), self.cell_to_segment.get(nb))
                    continue

                chain = [start, nb]
                prev, cur = start, nb
                while cur not in boundary:
                    nbs = [x for x in self._walkable_neighbors(cur, walkable) if x != prev]
                    if not nbs:
                        break
                    nxt = nbs[0]
                    visited_edges.add(edge_key(cur, nxt))
                    prev, cur = cur, nxt
                    chain.append(cur)
                    if cur in boundary:
                        break

                sid = self._new_id()
                seg = VisibilitySegment(
                    segment_id=sid,
                    level=self.level,
                    segment_type='corridor_segment',
                    cells=chain,
                    endpoints=[chain[0], chain[-1]],
                    direction_hint=self._direction_hint(chain[0], chain[-1]),
                )
                self._attach_adjacent_rooms(seg)
                self.segments[sid] = seg
                self._connect(sid, self.cell_to_segment.get(chain[0]))
                self._connect(sid, self.cell_to_segment.get(chain[-1]))

        # Attach room adjacency to boundary segments too.
        for seg in self.segments.values():
            self._attach_adjacent_rooms(seg)

        room_to_segments: Dict[str, List[str]] = {}
        for sid, seg in self.segments.items():
            for rid in seg.adjacent_rooms:
                room_to_segments.setdefault(rid, [])
                if sid not in room_to_segments[rid]:
                    room_to_segments[rid].append(sid)

        return {
            'segments': self.segments,
            'room_to_segments': room_to_segments,
            'stats': {
                'walkable_corridor_cells': len(walkable),
                'boundary_cells': len(boundary),
                'segments': len(self.segments),
                'rooms_with_segments': len(room_to_segments),
            },
        }

    def _corridor_walkable_cells(self) -> Set[Cell]:
        cells: Set[Cell] = set()
        for cell in self.grid.all_walkable():
            r, c = cell
            token = self.grid.get(r, c)
            in_room = any(rb.contains(cell) for rb in self.room_boxes)

            # Keep door/stair cells even if they lie on/inside room bbox. They are transition nodes.
            if token.startswith('D') or token.startswith('S'):
                cells.add(cell)
                continue

            # Plain floor inside a room is not a corridor visibility segment.
            if in_room:
                continue

            cells.add(cell)
        return cells

    def _boundary_cells(self, walkable: Set[Cell]) -> Set[Cell]:
        boundary: Set[Cell] = set()
        for cell in walkable:
            r, c = cell
            token = self.grid.get(r, c)
            deg = len(self._walkable_neighbors(cell, walkable))
            if token.startswith('D') or token.startswith('S'):
                boundary.add(cell)
                continue
            if deg != 2:
                boundary.add(cell)
                continue
            if self._touches_any_room(cell):
                # A corridor cell immediately adjacent to a room boundary is an actionable doorway approach.
                boundary.add(cell)
        return boundary

    def _create_boundary_segment(self, cell: Cell, walkable: Set[Cell]) -> str:
        sid = self._new_id()
        r, c = cell
        token = self.grid.get(r, c)
        deg = len(self._walkable_neighbors(cell, walkable))
        if token.startswith('S'):
            typ = 'stair'
        elif token.startswith('D'):
            typ = 'doorway'
        elif deg <= 1:
            typ = 'dead_end'
        elif deg >= 3:
            typ = 'junction'
        elif self._touches_any_room(cell):
            typ = 'doorway'
        else:
            typ = 'corridor_node'
        seg = VisibilitySegment(
            segment_id=sid,
            level=self.level,
            segment_type=typ,
            cells=[cell],
            endpoints=[cell],
        )
        self._attach_adjacent_rooms(seg)
        self.segments[sid] = seg
        self.cell_to_segment[cell] = sid
        return sid

    def _walkable_neighbors(self, cell: Cell, walkable: Set[Cell]) -> List[Cell]:
        r, c = cell
        nbs = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        return [x for x in nbs if x in walkable]

    def _touches_any_room(self, cell: Cell) -> bool:
        return any(rb.touches(cell, margin=self.WALK_MARGIN_TO_ROOM) for rb in self.room_boxes)

    def _attach_adjacent_rooms(self, seg: VisibilitySegment) -> None:
        for rb in self.room_boxes:
            for cell in seg.cells:
                if rb.touches(cell, margin=self.WALK_MARGIN_TO_ROOM):
                    if rb.room_id not in seg.adjacent_rooms:
                        seg.adjacent_rooms.append(rb.room_id)
                    break

    def _new_id(self) -> str:
        sid = f'{self.level_prefix}:HV{self._counter:04d}'
        self._counter += 1
        return sid

    def _connect(self, a: Optional[str], b: Optional[str]) -> None:
        if not a or not b or a == b:
            return
        if b not in self.segments[a].connected_segments:
            self.segments[a].connected_segments.append(b)
        if a not in self.segments[b].connected_segments:
            self.segments[b].connected_segments.append(a)

    @staticmethod
    def _direction_hint(a: Cell, b: Cell) -> str:
        dr = b[0] - a[0]
        dc = b[1] - a[1]
        if abs(dc) >= abs(dr):
            return 'east' if dc > 0 else 'west'
        return 'south' if dr > 0 else 'north'


def room_boxes_from_room_data(room_data: Dict[str, Dict[str, Any]], level: int) -> List[RoomBox]:
    boxes: List[RoomBox] = []
    marker = f':L{level:02d}:'
    for rid, room in room_data.items():
        if marker not in rid:
            continue
        raw = extract_donjon_raw(room)
        try:
            west = int(raw.get('west') if raw.get('west') is not None else raw.get('col'))
            east = int(raw.get('east') if raw.get('east') is not None else west)
            north = int(raw.get('north') if raw.get('north') is not None else raw.get('row'))
            south = int(raw.get('south') if raw.get('south') is not None else north)
        except Exception:
            continue
        boxes.append(RoomBox(rid, level, west, east, north, south))
    return boxes
