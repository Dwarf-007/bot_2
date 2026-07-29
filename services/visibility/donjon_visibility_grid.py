from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

Cell = Tuple[int, int]

class DonjonVisibilityGrid:
    """TSV alapú cellarács corridor visibility számításhoz.

    A Donjon TSV tokenekből konzervatív járhatósági rácsot készít.
    F = floor/járható cella. D* = ajtó/átjáró tokenek. SU/SD = lépcső tokenek.
    """

    def __init__(self, rows: List[List[str]]) -> None:
        self.rows = rows
        self.height = len(rows)
        self.width = max((len(r) for r in rows), default=0)

    @classmethod
    def from_tsv(cls, path: str | Path) -> 'DonjonVisibilityGrid':
        rows: List[List[str]] = []
        for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
            rows.append([cell.strip() for cell in line.split('\t')])
        return cls(rows)

    def get(self, row: int, col: int) -> str:
        if row < 0 or row >= self.height:
            return ''
        if col < 0 or col >= len(self.rows[row]):
            return ''
        return self.rows[row][col]

    def is_walkable(self, row: int, col: int) -> bool:
        token = self.get(row, col)
        if not token:
            return False
        if token == 'F':
            return True
        if token.startswith('D'):
            return True
        if token.startswith('S'):
            return True
        return False

    def is_door(self, row: int, col: int) -> bool:
        return self.get(row, col).startswith('D')

    def is_stair(self, row: int, col: int) -> bool:
        return self.get(row, col).startswith('S')

    def neighbors4(self, row: int, col: int) -> List[Cell]:
        return [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]

    def walkable_neighbors4(self, row: int, col: int) -> List[Cell]:
        return [(r, c) for r, c in self.neighbors4(row, col) if self.is_walkable(r, c)]

    def degree(self, row: int, col: int) -> int:
        return len(self.walkable_neighbors4(row, col))

    def all_walkable(self) -> Iterable[Cell]:
        for r in range(self.height):
            for c in range(len(self.rows[r])):
                if self.is_walkable(r, c):
                    yield (r, c)

    def token_summary(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for row in self.rows:
            for token in row:
                if token:
                    out[token] = out.get(token, 0) + 1
        return dict(sorted(out.items()))
