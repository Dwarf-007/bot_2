from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

@dataclass(frozen=True)
class TsvCell:
    row: int
    col: int
    token: str
    kind: str
    walkable: bool
    door_like: bool = False
    stair: Optional[str] = None

class DonjonTsvMap:
    def __init__(self, cells: List[List[TsvCell]]) -> None:
        self.cells = cells
        self.n_rows = len(cells)
        self.n_cols = max((len(r) for r in cells), default=0)
        self._by_pos = {(c.row, c.col): c for row in cells for c in row}

    def get(self, row: int, col: int) -> Optional[TsvCell]:
        return self._by_pos.get((row, col))

    def neighbors4(self, row: int, col: int) -> Iterable[TsvCell]:
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            cell = self.get(row+dr, col+dc)
            if cell:
                yield cell

    def walkable_neighbors4(self, row: int, col: int) -> Iterable[TsvCell]:
        for cell in self.neighbors4(row, col):
            if cell.walkable:
                yield cell

class DonjonTsvParser:
    # conservative defaults; tokens observed in Donjon TSV exports
    FLOOR = {'F'}
    STAIR_UP = {'SU', 'SUU'}
    STAIR_DOWN = {'SD', 'SDD'}
    DOOR_PREFIXES = ('D',)  # DL, DR, DT, DB, DPL, DPR, DSL, DSR, DST, DSB, DPT, DPB...

    @classmethod
    def parse_file(cls, path: str | Path) -> DonjonTsvMap:
        text = Path(path).read_text(encoding='utf-8')
        return cls.parse_text(text)

    @classmethod
    def parse_text(cls, text: str) -> DonjonTsvMap:
        rows: List[List[TsvCell]] = []
        for r, line in enumerate(text.splitlines()):
            raw_tokens = line.rstrip('\n').split('\t')
            row: List[TsvCell] = []
            for c, raw in enumerate(raw_tokens):
                token = raw.strip()
                row.append(cls._cell(r, c, token))
            rows.append(row)
        return DonjonTsvMap(rows)

    @classmethod
    def _cell(cls, row: int, col: int, token: str) -> TsvCell:
        if not token:
            return TsvCell(row, col, token, 'empty', False)
        stair = None
        if token in cls.STAIR_UP:
            stair = 'up'
        elif token in cls.STAIR_DOWN:
            stair = 'down'
        door_like = token.startswith(cls.DOOR_PREFIXES) or token.startswith(('S',)) and token not in cls.STAIR_UP | cls.STAIR_DOWN
        if token in cls.FLOOR:
            kind = 'floor'; walkable = True
        elif stair:
            kind = 'stair'; walkable = True
        elif token.startswith('D') or token.startswith('S'):
            kind = 'door'; walkable = True; door_like = True
        else:
            kind = 'marker'; walkable = True
        return TsvCell(row, col, token, kind, walkable, door_like, stair)

    @classmethod
    def token_summary(cls, grid: DonjonTsvMap) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for row in grid.cells:
            for cell in row:
                if cell.token:
                    result[cell.token] = result.get(cell.token, 0) + 1
        return dict(sorted(result.items()))
