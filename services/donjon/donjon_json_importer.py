"""
SERVICES/GENERATORS/DONJON_JSON_IMPORTER.PY

Imports Donjon dungeon JSON into the source-agnostic GeneratedDungeon model.

Sprint 1 scope:
- Parse Donjon `cells` bit-grid.
- Extract room ids and bounding boxes.
- Extract doors / arches / portcullises / secret / trapped / locked flags.
- Infer room-to-room connections through corridor/door networks.

Notes:
- Donjon stores many properties as bit flags in each grid cell.
- Room id is encoded with the `cell_bit.room_id` mask. The importer derives the
  shift from the mask dynamically, so it is not hard-coded to a single Donjon
  export version.
- Rich narrative text from the generated PDF is NOT imported here. Sprint 2/3
  will handle bundle conversion and optional enrichment.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from models.generated_dungeon import (
    GeneratedConnection,
    GeneratedDoor,
    GeneratedDungeon,
    GeneratedRoom,
    GeneratedTrap,
)
from services.generators.generator_provider import GenerationRequest

GridPoint = Tuple[int, int]


class DonjonJsonImporter:
    provider_name = "donjon_json"

    DEFAULT_BITS = {
        "nothing": 0,
        "blocked": 1,
        "room": 2,
        "corridor": 4,
        "perimeter": 16,
        "room_id": 65472,
        "arch": 65536,
        "door": 131072,
        "locked": 262144,
        "trapped": 524288,
        "secret": 1048576,
        "portcullis": 2097152,
        "stair_down": 4194304,
        "stair_up": 8388608,
        "label": 4278190080,
    }

    CARDINALS: list[tuple[str, int, int]] = [
        ("north", 0, -1),
        ("east", 1, 0),
        ("south", 0, 1),
        ("west", -1, 0),
    ]

    OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

    def generate(self, request: GenerationRequest) -> GeneratedDungeon:
        if not request.source_path:
            raise ValueError("GenerationRequest.source_path is required for DonjonJsonImporter")
        return self.import_file(
            request.source_path,
            dungeon_id=request.campaign_id,
            title=request.title,
            metadata=request.metadata,
        )

    def import_file(
        self,
        path: str | Path,
        dungeon_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GeneratedDungeon:
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        return self.import_data(
            data,
            dungeon_id=dungeon_id or source.stem,
            title=title or self._title_from_data(data, source.stem),
            metadata={"source_file": str(source), **(metadata or {})},
        )

    def import_data(
        self,
        data: Dict[str, Any],
        dungeon_id: str = "generated_dungeon",
        title: str = "Generated Dungeon",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GeneratedDungeon:
        cells = self._cells(data)
        bits = self._bits(data)
        height = len(cells)
        width = max((len(row) for row in cells), default=0)

        room_cells = self._collect_room_cells(cells, bits)
        rooms, entrance = self._build_rooms(room_cells, data=data, cells=cells, bits=bits)
        doors = self._collect_doors(cells, bits)
        traps = self._collect_traps(cells, bits, doors=doors)
        connections = self._infer_connections(cells, bits, room_cells, doors)
        rooms = self._attach_exits_to_rooms(rooms, connections)

        return GeneratedDungeon(
            dungeon_id=str(dungeon_id),
            title=str(title),
            source="donjon_json",
            width=width,
            height=height,
            rooms=rooms,
            connections=connections,
            doors=doors,
            traps=traps,
            entrance=entrance,
            metadata={
                "donjon_keys": sorted(str(key) for key in data.keys()),
                "cell_bit": bits,
                **(metadata or {}),
            },
        )

    def _cells(self, data: Dict[str, Any]) -> list[list[int]]:
        cells = data.get("cells") or []
        if not isinstance(cells, list):
            raise ValueError("Donjon JSON must contain a list field named 'cells'")
        normalized: list[list[int]] = []
        for row in cells:
            if isinstance(row, list):
                normalized.append([int(value or 0) for value in row])
        return normalized

    def _bits(self, data: Dict[str, Any]) -> Dict[str, int]:
        raw = data.get("cell_bit") or {}
        bits = dict(self.DEFAULT_BITS)
        if isinstance(raw, dict):
            for key, value in raw.items():
                try:
                    bits[str(key)] = int(value)
                except Exception:
                    pass
        return bits

    def _collect_room_cells(self, cells: list[list[int]], bits: Dict[str, int]) -> Dict[str, List[GridPoint]]:
        room_cells: dict[str, list[GridPoint]] = defaultdict(list)
        for y, row in enumerate(cells):
            for x, value in enumerate(row):
                if self._has(value, bits, "room"):
                    room_id = self._room_id(value, bits)
                    if room_id:
                        room_cells[str(room_id)].append((x, y))
        return dict(room_cells)

    def _build_rooms(self, room_cells: Dict[str, List[GridPoint]], data: Dict[str, Any], cells: Optional[List[List[int]]] = None, bits: Optional[Dict[str, int]] = None) -> Tuple[List[GeneratedRoom], Optional[Dict[str, Any]]]:
        explicit_titles = self._explicit_room_titles(data)
        entrance_room_id, entrance = self._choose_entrance(room_cells, cells, bits)
        rooms: list[GeneratedRoom] = []
        for index, room_id in enumerate(sorted(room_cells.keys(), key=self._natural_room_sort)):
            cells_pts = room_cells[room_id]
            xs = [x for x, _ in cells_pts]
            ys = [y for _, y in cells_pts]
            title = explicit_titles.get(room_id) or f"Room #{room_id}"
            rooms.append(
                GeneratedRoom(
                    room_id=str(room_id),
                    title=title,
                    x=min(xs),
                    y=min(ys),
                    width=max(xs) - min(xs) + 1,
                    height=max(ys) - min(ys) + 1,
                    cells=sorted(cells_pts, key=lambda p: (p[1], p[0])),
                    is_entrance=(str(room_id) == entrance_room_id),
                    metadata={"cell_count": len(cells_pts)},
                )
            )
        return rooms, entrance

    def _choose_entrance(self, room_cells: Dict[str, List[GridPoint]], cells: Optional[List[List[int]]], bits: Optional[Dict[str, int]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Bejárat/kezdőpont kiválasztása egyszintes dungeonhoz.

        A kezdőpontok a folyosó-/ajtócella (külső kijárat) vagy a lépcsőcellák közül
        kerülnek ki — a szobák alapesetben NEM kezdőpontok. A `candidates` lista az
        összes érvényes kezdőpontot tartalmazza; a tényleges bejárat a `x`/`y`
        koordináta (a visibility ehhez igazodik).
        """
        if not room_cells:
            return None, None
        first = str(sorted(room_cells.keys(), key=self._natural_room_sort)[0])
        if not cells or not bits:
            pts = room_cells.get(first, [])
            cell = pts[0] if pts else (0, 0)
            cand = {"x": cell[0], "y": cell[1], "kind": "room", "room_id": first}
            return first, {**cand, "source": "default_room", "description": "Beléptetek a terembe.", "candidates": [cand]}

        # Összes érvényes kezdőpont: lépcsők + külső kijárati folyosó/ajtók
        candidates: List[Dict[str, Any]] = []
        for y, row in enumerate(cells):
            for x, value in enumerate(row):
                if self._has(value, bits, "stair_up"):
                    candidates.append({"x": x, "y": y, "kind": "stair_up", "room_id": self._room_id_for_cell(room_cells, x, y)})
                elif self._has(value, bits, "stair_down"):
                    candidates.append({"x": x, "y": y, "kind": "stair_down", "room_id": self._room_id_for_cell(room_cells, x, y)})
        for (x, y) in sorted(self._compute_egress_cells(cells, bits)):
            kind = "door" if self._is_connector(cells[y][x], bits) else "corridor"
            candidates.append({"x": x, "y": y, "kind": kind, "room_id": self._room_id_for_egress(room_cells, cells, bits, x, y)})

        if candidates:
            chosen = dict(random.choice(candidates))
            if chosen["kind"] in ("stair_up", "stair_down"):
                chosen["source"] = "stair"
                chosen["description"] = "Mögöttetek a lépcső, amin a labirintusba jöttetek."
            else:
                chosen["source"] = "external_exit"
                chosen["description"] = (
                    "Beléptetek az ajtón át a folyosóra, amely befelé vezet."
                    if chosen["kind"] == "door"
                    else "Beléptetek a folyosóra, amely befelé vezet."
                )
            chosen["candidates"] = candidates
            return chosen["room_id"], chosen

        # Fallback: 1. szoba (nincs folyosó/lépcső)
        pts = room_cells.get(first, [])
        cell = pts[0] if pts else (0, 0)
        cand = {"x": cell[0], "y": cell[1], "kind": "room", "room_id": first}
        return first, {**cand, "source": "default_room", "description": "Beléptetek a terembe.", "candidates": [cand]}

    def _room_id_for_cell(self, room_cells: Dict[str, List[GridPoint]], x: int, y: int) -> Optional[str]:
        for rid, pts in room_cells.items():
            if (x, y) in pts:
                return str(rid)
        return None

    def _room_id_for_egress(self, room_cells: Dict[str, List[GridPoint]], cells: List[List[int]], bits: Dict[str, int], x: int, y: int) -> Optional[str]:
        """A kijárati folyosócellához kapcsolódó szoba megkeresése (folyosóhálózaton át)."""
        seen: set = {(x, y)}
        q: deque = deque([(x, y)])
        while q:
            cx, cy = q.popleft()
            if self._in_bounds(cells, cx, cy) and self._is_room(cells[cy][cx], bits):
                return self._room_id_for_cell(room_cells, cx, cy)
            for _, nx, ny in self._neighbors(cx, cy):
                if not self._in_bounds(cells, nx, ny):
                    continue
                v = cells[ny][nx]
                if self._is_room(v, bits) or self._has(v, bits, "corridor") or self._is_connector(v, bits):
                    if (nx, ny) not in seen:
                        seen.add((nx, ny))
                        q.append((nx, ny))
        return None

    def _compute_egress_cells(self, cells: List[List[int]], bits: Dict[str, int]) -> set:
        """Külső kijárati cellák: a dungeon külső határfalához (perimeter) közvetlenül
        csatlakozó folyosó-/ajtócellák. Külső határfal az a perimeter cella, amelynek a
        túloldalán a dungeonon kívüli (bleed) terület van — nem pedig belső fal, amit
        szobák vesznek körül.
        """
        H = len(cells)
        W = len(cells[0]) if H else 0

        def is_dungeon(x: int, y: int) -> bool:
            if not self._in_bounds(cells, x, y):
                return False
            v = cells[y][x]
            return (
                self._is_room(v, bits)
                or self._has(v, bits, "corridor")
                or self._is_connector(v, bits)
                or self._has(v, bits, "perimeter")
            )

        # Bleed: a dungeonon kívüli terület (grid szélétől elérhető, nem-dungeon cellák).
        # A perimeter gyűrű zárt, így a belső üres cellák nem kerülnek ide.
        bleed: set = set()
        q: deque = deque()
        for x in range(W):
            for y in (0, H - 1):
                if self._in_bounds(cells, x, y) and not is_dungeon(x, y):
                    bleed.add((x, y))
                    q.append((x, y))
        for y in range(H):
            for x in (0, W - 1):
                if self._in_bounds(cells, x, y) and not is_dungeon(x, y) and (x, y) not in bleed:
                    bleed.add((x, y))
                    q.append((x, y))
        while q:
            x, y = q.popleft()
            for _, nx, ny in self._neighbors(x, y):
                if self._in_bounds(cells, nx, ny) and not is_dungeon(nx, ny) and (nx, ny) not in bleed:
                    bleed.add((nx, ny))
                    q.append((nx, ny))

        egress: set = set()
        for y in range(H):
            for x in range(W):
                if not self._in_bounds(cells, x, y) or not self._has(cells[y][x], bits, "perimeter"):
                    continue
                if any((nx, ny) in bleed for _, nx, ny in self._neighbors(x, y)):
                    for _, nx, ny in self._neighbors(x, y):
                        if self._in_bounds(cells, nx, ny) and (
                            self._has(cells[ny][nx], bits, "corridor") or self._is_connector(cells[ny][nx], bits)
                        ):
                            egress.add((nx, ny))
        return egress


    def _explicit_room_titles(self, data: Dict[str, Any]) -> Dict[str, str]:
        titles: dict[str, str] = {}
        rooms = data.get("rooms") or data.get("room") or {}
        if isinstance(rooms, dict):
            for key, value in rooms.items():
                if isinstance(value, dict):
                    title = value.get("title") or value.get("name")
                else:
                    title = str(value) if value else None
                if title:
                    titles[str(key)] = str(title)
        elif isinstance(rooms, list):
            for item in rooms:
                if isinstance(item, dict):
                    room_id = item.get("room_id") or item.get("id") or item.get("number")
                    title = item.get("title") or item.get("name")
                    if room_id and title:
                        titles[str(room_id)] = str(title)
        return titles

    def _collect_doors(self, cells: list[list[int]], bits: Dict[str, int]) -> List[GeneratedDoor]:
        doors: list[GeneratedDoor] = []
        counter = 0
        for y, row in enumerate(cells):
            for x, value in enumerate(row):
                if self._is_connector(value, bits):
                    counter += 1
                    kind = self._connector_kind(value, bits)
                    doors.append(
                        GeneratedDoor(
                            door_id=f"door_{counter:04d}",
                            x=x,
                            y=y,
                            kind=kind,
                            locked=self._has(value, bits, "locked"),
                            trapped=self._has(value, bits, "trapped"),
                            secret=self._has(value, bits, "secret"),
                            metadata={"raw_cell": int(value)},
                        )
                    )
        return doors

    def _collect_traps(self, cells: list[list[int]], bits: Dict[str, int], doors: List[GeneratedDoor]) -> List[GeneratedTrap]:
        traps: list[GeneratedTrap] = []
        seen: set[tuple[int, int]] = set()
        for door in doors:
            if door.trapped:
                traps.append(
                    GeneratedTrap(
                        trap_id=f"trap_{len(traps)+1:04d}",
                        x=door.x,
                        y=door.y,
                        kind="door_trap",
                        description=f"Trapped {door.kind}",
                        metadata={"door_id": door.door_id},
                    )
                )
                seen.add((door.x, door.y))
        for y, row in enumerate(cells):
            for x, value in enumerate(row):
                if (x, y) in seen:
                    continue
                if self._has(value, bits, "trapped"):
                    traps.append(
                        GeneratedTrap(
                            trap_id=f"trap_{len(traps)+1:04d}",
                            x=x,
                            y=y,
                            kind="cell_trap",
                            description="Trapped dungeon cell",
                            metadata={"raw_cell": int(value)},
                        )
                    )
        return traps

    def _infer_connections(
        self,
        cells: list[list[int]],
        bits: Dict[str, int],
        room_cells: Dict[str, List[GridPoint]],
        doors: List[GeneratedDoor],
    ) -> List[GeneratedConnection]:
        point_to_room: dict[GridPoint, str] = {}
        for room_id, points in room_cells.items():
            for point in points:
                point_to_room[point] = room_id

        door_by_point = {(door.x, door.y): door for door in doors}
        boundary_starts: dict[str, set[GridPoint]] = defaultdict(set)

        for room_id, points in room_cells.items():
            for x, y in points:
                for _, nx, ny in self._neighbors(x, y):
                    if not self._in_bounds(cells, nx, ny):
                        continue
                    npoint = (nx, ny)
                    if point_to_room.get(npoint) == room_id:
                        continue
                    nvalue = cells[ny][nx]
                    if self._is_passable_non_room(nvalue, bits):
                        boundary_starts[room_id].add(npoint)
                    elif self._is_room(nvalue, bits):
                        other = point_to_room.get(npoint)
                        if other and other != room_id:
                            boundary_starts[room_id].add(npoint)

        connections_by_key: dict[tuple[str, str], GeneratedConnection] = {}
        max_steps = max(256, len(cells) * max((len(row) for row in cells), default=1))

        for start_room, starts in boundary_starts.items():
            for start in starts:
                found = self._bfs_to_rooms(
                    cells=cells,
                    bits=bits,
                    point_to_room=point_to_room,
                    start=start,
                    start_room=start_room,
                    door_by_point=door_by_point,
                    max_steps=max_steps,
                )
                for other_room, distance, path_doors in found:
                    if other_room == start_room:
                        continue
                    a, b = sorted([str(start_room), str(other_room)], key=self._natural_room_sort)
                    key = (a, b)
                    via = self._via_from_doors(path_doors)
                    locked = any(door.locked for door in path_doors)
                    trapped = any(door.trapped for door in path_doors)
                    secret = any(door.secret for door in path_doors)
                    direction = self._direction_between_rooms(room_cells.get(start_room, []), room_cells.get(other_room, []))
                    candidate = GeneratedConnection(
                        from_room_id=a,
                        to_room_id=b,
                        direction=direction,
                        via=via,
                        door_ids=sorted({door.door_id for door in path_doors}),
                        distance=distance,
                        locked=locked,
                        trapped=trapped,
                        secret=secret,
                    )
                    current = connections_by_key.get(key)
                    if current is None or candidate.distance < current.distance:
                        connections_by_key[key] = candidate

        return sorted(
            connections_by_key.values(),
            key=lambda c: (self._natural_room_sort(c.from_room_id), self._natural_room_sort(c.to_room_id)),
        )

    def _bfs_to_rooms(
        self,
        cells: list[list[int]],
        bits: Dict[str, int],
        point_to_room: Dict[GridPoint, str],
        start: GridPoint,
        start_room: str,
        door_by_point: Dict[GridPoint, GeneratedDoor],
        max_steps: int,
    ) -> list[tuple[str, int, list[GeneratedDoor]]]:
        queue = deque([(start, 0, [])])
        visited: set[GridPoint] = {start}
        found: list[tuple[str, int, list[GeneratedDoor]]] = []

        while queue and len(visited) <= max_steps:
            (x, y), distance, path_doors = queue.popleft()
            if not self._in_bounds(cells, x, y):
                continue
            point = (x, y)
            value = cells[y][x]
            new_path_doors = path_doors
            if point in door_by_point:
                new_path_doors = [*path_doors, door_by_point[point]]

            room_id = point_to_room.get(point)
            if room_id and room_id != start_room:
                found.append((room_id, distance, new_path_doors))
                continue

            if room_id == start_room:
                continue

            if not self._is_passable_non_room(value, bits):
                continue

            for _, nx, ny in self._neighbors(x, y):
                npoint = (nx, ny)
                if npoint in visited or not self._in_bounds(cells, nx, ny):
                    continue
                nvalue = cells[ny][nx]
                nroom = point_to_room.get(npoint)
                if nroom == start_room:
                    continue
                if nroom or self._is_passable_non_room(nvalue, bits):
                    visited.add(npoint)
                    queue.append((npoint, distance + 1, new_path_doors))
        return found

    def _attach_exits_to_rooms(self, rooms: List[GeneratedRoom], connections: List[GeneratedConnection]) -> List[GeneratedRoom]:
        exits_by_room: dict[str, dict[str, str]] = defaultdict(dict)
        for connection in connections:
            direction = connection.direction or f"to_{connection.to_room_id}"
            exits_by_room[connection.from_room_id][direction] = connection.to_room_id
            reverse = self.OPPOSITE.get(direction, f"to_{connection.from_room_id}")
            exits_by_room[connection.to_room_id][reverse] = connection.from_room_id

        updated: list[GeneratedRoom] = []
        for room in rooms:
            updated.append(
                GeneratedRoom(
                    room_id=room.room_id,
                    title=room.title,
                    x=room.x,
                    y=room.y,
                    width=room.width,
                    height=room.height,
                    cells=room.cells,
                    exits=dict(sorted(exits_by_room.get(room.room_id, {}).items())),
                    features=room.features,
                    monsters=room.monsters,
                    traps=room.traps,
                    treasures=room.treasures,
                    is_entrance=room.is_entrance,
                    metadata=room.metadata,
                )
            )
        return updated

    def _direction_between_rooms(self, a_cells: List[GridPoint], b_cells: List[GridPoint]) -> Optional[str]:
        if not a_cells or not b_cells:
            return None
        ax = sum(x for x, _ in a_cells) / len(a_cells)
        ay = sum(y for _, y in a_cells) / len(a_cells)
        bx = sum(x for x, _ in b_cells) / len(b_cells)
        by = sum(y for _, y in b_cells) / len(b_cells)
        dx = bx - ax
        dy = by - ay
        if abs(dx) >= abs(dy):
            return "east" if dx > 0 else "west"
        return "south" if dy > 0 else "north"

    def _via_from_doors(self, doors: List[GeneratedDoor]) -> str:
        if not doors:
            return "corridor"
        if any(door.secret for door in doors):
            return "secret"
        if any(door.kind == "portcullis" for door in doors):
            return "portcullis"
        if any(door.kind == "arch" for door in doors):
            return "arch"
        return "door"

    def _connector_kind(self, value: int, bits: Dict[str, int]) -> str:
        if self._has(value, bits, "stair_up"):
            return "stair_up"
        if self._has(value, bits, "stair_down"):
            return "stair_down"
        if self._has(value, bits, "secret"):
            return "secret"
        if self._has(value, bits, "portcullis"):
            return "portcullis"
        if self._has(value, bits, "arch"):
            return "arch"
        if self._has(value, bits, "door"):
            return "door"
        return "connector"

    def _is_connector(self, value: int, bits: Dict[str, int]) -> bool:
        return any(
            self._has(value, bits, key)
            for key in ("door", "arch", "portcullis", "secret", "stair_up", "stair_down")
        )

    def _is_passable_non_room(self, value: int, bits: Dict[str, int]) -> bool:
        if self._is_room(value, bits):
            return False
        return self._has(value, bits, "corridor") or self._is_connector(value, bits)

    def _is_room(self, value: int, bits: Dict[str, int]) -> bool:
        return self._has(value, bits, "room") and bool(self._room_id(value, bits))

    def _has(self, value: int, bits: Dict[str, int], key: str) -> bool:
        mask = int(bits.get(key, 0) or 0)
        if mask == 0:
            return False
        return (int(value) & mask) != 0

    def _room_id(self, value: int, bits: Dict[str, int]) -> int:
        mask = int(bits.get("room_id", 0) or 0)
        if not mask:
            return 0
        low_bit = mask & -mask
        shift = low_bit.bit_length() - 1
        return int((int(value) & mask) >> shift)

    def _neighbors(self, x: int, y: int) -> Iterable[tuple[str, int, int]]:
        for direction, dx, dy in self.CARDINALS:
            yield direction, x + dx, y + dy

    def _in_bounds(self, cells: list[list[int]], x: int, y: int) -> bool:
        return 0 <= y < len(cells) and 0 <= x < len(cells[y])

    @staticmethod
    def _natural_room_sort(room_id: str) -> tuple[int, str]:
        text = str(room_id)
        try:
            return int(text), text
        except Exception:
            return 10**9, text

    @staticmethod
    def _title_from_data(data: Dict[str, Any], fallback: str) -> str:
        for key in ("title", "name", "dungeon_name"):
            value = data.get(key)
            if value:
                return str(value)
        return fallback.replace("_", " ").strip() or "Donjon Dungeon"
