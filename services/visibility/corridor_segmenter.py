from __future__ import annotations
from collections import deque, defaultdict
from typing import Dict, List, Set, Tuple

from models.corridor_visibility_models import VisibilitySegment
from services.visibility.donjon_visibility_grid import DonjonVisibilityGrid, Cell

class CorridorSegmenter:
    """TSV cellarácsból corridor segmenteket és junction node-okat készít.

    Kulcsötlet:
    - junction/dead-end/door/stair cellák önálló node-szerű határpontok,
    - degree==2 folyosócellákból egyenes vagy görbülő segmentek épülnek két határpont között.
    """

    def __init__(self, grid: DonjonVisibilityGrid, level: int, level_prefix: str) -> None:
        self.grid = grid
        self.level = level
        self.level_prefix = level_prefix

    def build_segments(self) -> Dict[str, VisibilitySegment]:
        walkable = set(self.grid.all_walkable())
        boundary: Set[Cell] = set()
        for cell in walkable:
            r, c = cell
            deg = self.grid.degree(r, c)
            if deg != 2 or self.grid.is_door(r, c) or self.grid.is_stair(r, c):
                boundary.add(cell)

        segments: Dict[str, VisibilitySegment] = {}
        cell_to_segment: Dict[Cell, str] = {}
        counter = 1

        # Boundary cells as explicit nodes
        for cell in sorted(boundary):
            r, c = cell
            token = self.grid.get(r, c)
            deg = self.grid.degree(r, c)
            if self.grid.is_stair(r, c):
                typ = 'stair'
            elif self.grid.is_door(r, c):
                typ = 'doorway'
            elif deg <= 1:
                typ = 'dead_end'
            elif deg >= 3:
                typ = 'junction'
            else:
                typ = 'corridor_node'
            sid = self._sid(counter); counter += 1
            segments[sid] = VisibilitySegment(sid, self.level, typ, cells=[cell], endpoints=[cell])
            cell_to_segment[cell] = sid

        visited_edges: Set[Tuple[Cell, Cell]] = set()
        def ekey(a: Cell, b: Cell) -> Tuple[Cell, Cell]: return tuple(sorted([a, b]))  # type: ignore

        # Build chains from boundary through degree-2 cells to next boundary
        for start in sorted(boundary):
            for nb in self.grid.walkable_neighbors4(*start):
                key = ekey(start, nb)
                if key in visited_edges:
                    continue
                visited_edges.add(key)
                if nb in boundary:
                    self._connect(segments, cell_to_segment[start], cell_to_segment[nb])
                    continue
                chain = [start, nb]
                prev, cur = start, nb
                while cur not in boundary:
                    nbs = [x for x in self.grid.walkable_neighbors4(*cur) if x != prev]
                    if not nbs:
                        break
                    nxt = nbs[0]
                    visited_edges.add(ekey(cur, nxt))
                    prev, cur = cur, nxt
                    chain.append(cur)
                if len(chain) >= 2:
                    end = chain[-1]
                    sid = self._sid(counter); counter += 1
                    # Chain segment excludes boundary endpoints from cells? Keep all for visibility/rendering.
                    segments[sid] = VisibilitySegment(
                        sid, self.level, 'corridor_segment', cells=chain, endpoints=[chain[0], chain[-1]],
                        direction_hint=self._direction_hint(chain[0], chain[-1]),
                    )
                    if chain[0] in cell_to_segment:
                        self._connect(segments, sid, cell_to_segment[chain[0]])
                    if end in cell_to_segment:
                        self._connect(segments, sid, cell_to_segment[end])

        return segments

    def _sid(self, i: int) -> str:
        return f'{self.level_prefix}:VS{i:04d}'

    @staticmethod
    def _connect(segments: Dict[str, VisibilitySegment], a: str, b: str) -> None:
        if not a or not b or a == b:
            return
        if b not in segments[a].connected_segments:
            segments[a].connected_segments.append(b)
        if a not in segments[b].connected_segments:
            segments[b].connected_segments.append(a)

    @staticmethod
    def _direction_hint(a: Cell, b: Cell) -> str:
        dr, dc = b[0] - a[0], b[1] - a[1]
        if abs(dc) >= abs(dr):
            return 'east' if dc > 0 else 'west'
        return 'south' if dr > 0 else 'north'
