# services/donjon/node_graph_builder.py
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from models.node_graph_models import Node, NodeEdge, NodeGraph

CELL_BITS = {
    "block": 1,
    "room": 2,
    "corridor": 4,
    "perimeter": 16,
    "aperture": 32,
    "arch": 65536,
    "door": 131072,
    "portcullis": 2097152,
    "secret": 1048576,
    "locked": 262144,
    "trapped": 524288,
    "stair_down": 4194304,
    "stair_up": 8388608,
    "room_id": 65472,
}


def has_bit(value: int, bit: int) -> bool:
    return (value & bit) != 0


class NodeGraphBuilder:
    def __init__(self, campaign_id: str, dungeon_id: str = None, title: str = None) -> None:
        self.campaign_id = campaign_id
        self.dungeon_id = dungeon_id or campaign_id
        self.title = title or self.dungeon_id
        self._level_data: Dict[int, dict] = {}
        self._all_stairs: Dict[int, list] = {}
        self._corridor_features: Dict[int, dict] = {}
        self._cell_map: Dict[int, Dict[Tuple[int, int], str]] = defaultdict(dict)
        self._processed: Dict[int, Set[Tuple[int, int]]] = defaultdict(set)

    def build_from_manifest(self, manifest_file: str | Path) -> NodeGraph:
        manifest_path = Path(manifest_file)
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        graph = NodeGraph(
            campaign_id=self.campaign_id,
            dungeon_id=self.dungeon_id,
            title=self.title,
            metadata={'source_manifest': str(manifest_path), 'plan': manifest.get('plan', {})},
        )

        for level_info in manifest.get('levels', []):
            level = int(level_info['level'])
            json_file = self._resolve_file(level_info, manifest_path.parent, 'json')
            if not json_file:
                continue
            data = json.loads(json_file.read_text(encoding='utf-8'))
            self._level_data[level] = data
            self._all_stairs[level] = data.get('stairs', [])
            self._corridor_features[level] = data.get('corridor_features', {})

        # 1. Szobák
        for level in self._level_data:
            self._add_room_nodes(graph, level)

        # 2. Külvilág hozzáadása és ajtók kizárása
        self._add_outside_node(graph, manifest)
        for level in self._level_data:
            self._mark_doors(graph, level)

        # 3. Folyosók felépítése (JAVÍTOTT)
        for level in self._level_data:
            self._build_corridors(graph, level)

        # 4. Lépcsők
        self._add_stair_edges(graph, manifest)

        # 5. Átjárók (ajtók, egress)
        for level in self._level_data:
            self._mark_doors_and_egress(graph, level)



        # Bejárat
        self._mark_entrance(graph, manifest)

        graph.metadata.update({
            'node_count': len(graph.nodes),
            'edge_count': len(graph.edges),
            'builder_version': 'node_graph_builder_v4_cell_map_fixed',
        })
        return graph

    # -----------------------------------------------------------------
    # 1. Szoba csomópontok
    # -----------------------------------------------------------------
    def _add_room_nodes(self, graph: NodeGraph, level: int) -> None:
        data = self._level_data[level]
        for raw in data.get('rooms') or []:
            if not isinstance(raw, dict):
                continue
            rid = raw.get('id')
            if rid is None:
                continue
            room_id = f'{self.campaign_id}:L{level:02d}:R{int(rid):03d}'
            north = raw.get('north') or raw.get('row') or 0
            south = raw.get('south') or north
            west = raw.get('west') or raw.get('col') or 0
            east = raw.get('east') or west
            cells = [(r, c) for r in range(int(north), int(south) + 1) for c in range(int(west), int(east) + 1)]
            for cell in cells:
                self._cell_map[level][cell] = room_id
                self._processed[level].add(cell)
            cells = [(north, west), (south, east)]
            center = ((north + south) / 2, (west + east) / 2)
            title = f'Level {level} Room #{rid}'
            facts = raw.get('facts', '') or raw.get('contents', {}).get('summary', '')
            node = Node(
                node_id=room_id, campaign_id=self.campaign_id, level=level,
                type='room', title=title, description=facts,
                cells=cells, center=center, raw=raw,
            )
            graph.nodes[room_id] = node



    # -----------------------------------------------------------------
    # 2. Külvilág hozzáadása és ajtók kizárása
    # -----------------------------------------------------------------

    def _add_outside_node(self, graph: NodeGraph, manifest: dict) -> None:
        outside_id = f'{self.campaign_id}:outside'
        plan = manifest.get('plan', {})
        direction = plan.get('default_direction', 'down')
        levels = sorted(self._level_data.keys())
        if levels:
            outside_level = levels[0] if direction == 'down' else levels[-1] + 1
        else:
            outside_level = 1
        graph.nodes[outside_id] = Node(
            node_id=outside_id, campaign_id=self.campaign_id, level=outside_level,
            type='outside', title='Külvilág',
            description='A dungeon bejárata előtt állsz. A szabad ég alatt.',
            cells=[], center=(0.0, 0.0),
        )


    def _mark_doors(self, graph: NodeGraph, level: int) -> None:
        data = self._level_data[level]
        cells_grid = data.get('cells')
        if not cells_grid:
            return

        for raw in data.get('rooms') or []:
            if not isinstance(raw, dict):
                continue
            rid = raw.get('id')
            if rid is None:
                continue
            room_id = f'{self.campaign_id}:L{level:02d}:R{int(rid):03d}'
            doors = raw.get('doors', {})
            for direction, entries in doors.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    door_row = e.get('row')
                    door_col = e.get('col')
                    if door_row is None or door_col is None:
                        continue
                    edge_id = f'door_{level}_{door_row}_{door_col}'
                    self._cell_map[level][(door_row, door_col)] = edge_id
                    self._processed[level].add((door_row, door_col))

  
    # -----------------------------------------------------------------
    # 3. Folyosók felépítése (JAVÍTOTT)
    # -----------------------------------------------------------------
    def _build_corridors(self, graph: NodeGraph, level: int) -> None:
        data = self._level_data[level]
        cells_grid = data.get('cells')
        if not cells_grid:
            return
        n_rows = len(cells_grid)
        n_cols = len(cells_grid[0]) if n_rows > 0 else 0

        node_counter = 1

        def is_free_cell(r, c):
            if not (0 <= r < n_rows and 0 <= c < n_cols):
                return False
            if (r, c) in self._processed[level]:
                return False
            val = cells_grid[r][c]
            return val != 0 and not has_bit(val, CELL_BITS["perimeter"])

        # Vízszintes folyosók
        for r in range(1, n_rows - 1):
            c = 1
            while c < n_cols - 1:
                if is_free_cell(r, c) and not is_free_cell(r, c - 1):
                    if is_free_cell(r, c + 1):
                        start_c = c
                        while is_free_cell(r, c):
                            c += 1
                        end_c = c - 1
                        
                        node_id = f'{self.campaign_id}:L{level:02d}:C{node_counter:04d}'
                        node_counter += 1
                        
                        # Minden érintett cellához elmentjük a folyosó ID-ját
                        for col in range(start_c, end_c + 1):
                            self._cell_map[level][(r, col)] = node_id
                        
                        cells = [(r, start_c), (r, end_c)] # Javítva a zárójel
                        center = (r, (start_c + end_c) / 2)
                        
                        node = Node(
                            node_id=node_id, campaign_id=self.campaign_id, level=level,
                            type='corridor', title='Folyosó',
                            description=self._corridor_description(level, cells_grid, cells),
                            cells=cells, center=center, orientation='horizontal',
                        )
                        graph.nodes[node_id] = node
                    else:
                        # Egycellás zsákutca
                        if not is_free_cell(r - 1, c) and not is_free_cell(r + 1, c):
                            node_id = f'{self.campaign_id}:L{level:02d}:C{node_counter:04d}'
                            node_counter += 1
                            
                            self._cell_map[level][(r, c)] = node_id
                            
                            node = Node(
                                node_id=node_id, campaign_id=self.campaign_id, level=level,
                                type='corridor', title='Folyosó',
                                description=self._corridor_description(level, cells_grid, [(r, c)]),
                                cells=[(r, c), (r, c)], center=(r, c), orientation=None,
                            )
                            graph.nodes[node_id] = node
                        c += 1
                else:
                    c += 1

        # Függőleges folyosók
        for c in range(1, n_cols - 1):
            r = 1
            while r < n_rows - 1:
                if is_free_cell(r, c) and not is_free_cell(r - 1, c) and is_free_cell(r + 1, c):
                    start_r = r
                    while is_free_cell(r, c):
                        r += 1
                    end_r = r - 1
                    
                    # JAVÍTÁS: Előbb generáljuk le az ID-t, hogy elérhető legyen a cellák mentésekor!
                    node_id = f'{self.campaign_id}:L{level:02d}:C{node_counter:04d}'
                    node_counter += 1
                    
                    # Minden érintett cellához elmentjük a folyosó ID-ját
                    for row in range(start_r, end_r + 1):
                        existing_node_id = self._cell_map[level].get((row, c))
    
                        if existing_node_id:
                            # Duplikáció szűrése: Elég egyszer behuzalozni ezt a két folyosószakaszt
                            edge_check_id = f'{node_id}->{existing_node_id}:east:corridor_link'
                            if edge_check_id not in graph.edges:
            
                                # --- A FÜGGŐLEGES FOLYOSÓBÓL VALÓ KILÉPÉS IRÁNYAI ---
                                # Ha a függőlegesen állsz, keletre vagy nyugatra fordulva lépsz át a vízszintesbe:
                                if is_free_cell(row, c + 1):
                                    self._create_edge(graph, node_id, existing_node_id, 'east', 'Kanyarodás vízszintes folyosóra', 'corridor_link')
                                if is_free_cell(row, c - 1):
                                    self._create_edge(graph, node_id, existing_node_id, 'west', 'Kanyarodás vízszintes folyosóra', 'corridor_link')
            
                                # --- A VÍZSZINTES FOLYOSÓBÓL VALÓ KILÉPÉS IRÁNYAI ---
                                # Ha a vízszintesben állsz, északra vagy délre fordulva lépsz át a függőlegesbe:
                                if is_free_cell(row - 1, c):
                                    self._create_edge(graph, existing_node_id, node_id, 'north', 'Kanyarodás függőleges folyosóra', 'corridor_link')
                                if is_free_cell(row + 1, c):
                                    self._create_edge(graph, existing_node_id, node_id, 'south', 'Kanyarodás függőleges folyosóra', 'corridor_link')
                        else:
                            self._cell_map[level][(row, c)] = node_id
                        
                    cells = [(start_r, c), (end_r, c)]
                    center = ((start_r + end_r) / 2, c)
                    
                    node = Node(
                        node_id=node_id, campaign_id=self.campaign_id, level=level,
                        type='corridor', title='Folyosó',
                        description=self._corridor_description(level, cells_grid, cells),
                        cells=cells, center=center, orientation='vertical',
                    )

                    graph.nodes[node_id] = node
                else:
                    r += 1


    # -----------------------------------------------------------------
    # 4. Lépcsők
    # -----------------------------------------------------------------

    def _add_stair_edges(self, graph: NodeGraph, manifest: dict) -> None:
        plan = manifest.get('plan', {})
        direction = plan.get('default_direction', 'down')
        outside_id = f'{self.campaign_id}:outside'
        levels = sorted(self._level_data.keys())
        if not levels:
            return

        stair_nodes: Dict[Tuple[int, str], str] = {}
        for level, stairs in self._all_stairs.items():
            for stair in stairs:
                row, col = stair['row'], stair['col']
                key = stair['key']
                coordinate =(row, col)
                stair_nodes[(level, key)] = coordinate

        top_level = levels[0]
        coordinate_up = stair_nodes.get((top_level, 'up'))

        if coordinate_up:
            target_id = self._cell_map[top_level].get(coordinate_up)
            self._create_edge(graph, outside_id, target_id, direction, 'Lépcső a kazamatába', 'stair')
            self._create_edge(graph, target_id, outside_id, self._opposite_direction(direction), 'Lépcső vissza a felszínre', 'stair')
        for i in range(len(levels) - 1):
            lev = levels[i]
            nxt = levels[i + 1]

            coord_down = stair_nodes.get((lev, 'down'))
            coord_up = stair_nodes.get((nxt, 'up'))

            if coord_down and coord_up:
                id_down = self._cell_map[level].get(coord_down)
                id_up = self._cell_map[level].get(coord_up)
                if id_down and id_up:
                    self._create_edge(graph, id_down, id_up, direction, 'Lépcső lefelé', 'stair')
                    self._create_edge(graph, id_up, id_down,  self._opposite_direction(direction), 'Lépcső felfelé', 'stair')


    # -----------------------------------------------------------------
    # 5. Átjárók (ajtók és egress)
    # -----------------------------------------------------------------
    def _mark_doors_and_egress(self, graph: NodeGraph, level: int) -> None:
        data = self._level_data[level]
        cells_grid = data.get('cells')
        settings = data.get('settings', {})
        max_row = int(settings.get('max_row'))
        max_col = int(settings.get('max_col'))
        if not cells_grid:
            return

        for raw in data.get('rooms') or []:
            if not isinstance(raw, dict):
                continue
            rid = raw.get('id')
            if rid is None:
                continue
            room_id = f'{self.campaign_id}:L{level:02d}:R{int(rid):03d}'
            doors = raw.get('doors', {})
            for direction, entries in doors.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    door_row = e.get('row')
                    door_col = e.get('col')
                    if door_row is None or door_col is None:
                        continue
                    if door_row == 0 or door_row == max_row or door_col == 0 or door_col == max_col:
                        # Ez egy egress ajtó! A szobát közvetlenül a külvilággal kötjük össze
                        self._create_edge_from_door(graph, room_id, outside_id, direction, e)

                    else:
                        neighbor_row = door_row
                        neighbor_col = door_col
  
                        if direction == 'north':
                            neighbor_row -= 1
                        elif direction == 'south':
                            neighbor_row += 1
                        elif direction == 'west':
                            neighbor_col -= 1
                        elif direction == 'east':
                            neighbor_col += 1
                        neighbor_id = self._cell_map[level].get((neighbor_row, neighbor_col))
                
                        if neighbor_id:
                            self._create_edge_from_door(graph, room_id, neighbor_id, direction, e)



        egress_list = data.get('egress', [])
        for eg in egress_list:
            if egress.get('type') == 'corridor':
                row = eg.get('row')
                col = eg.get('col')
                dir = eg.get['dir']
                if row is None or col is None:
                    continue
            corridor_node_id = self._cell_map[level].get((egr_row, egr_col))
            outside_id = f'{self.campaign_id}:outside'
            if corridor_node_id:
                self._create_edge(graph, corridor_node_id, outside_id, egr_dir, 'Folyosó végi kijárat', 'egress')
                self._create_edge(graph, outside_id, corridor_node_id, self._opposite_direction(egr_dir), 'Folyosó bejárat', 'egress')


    # -----------------------------------------------------------------
    # Segédeszközök
    # -----------------------------------------------------------------
    def _create_edge_from_door(self, graph: NodeGraph, from_id: str, to_id: str, direction: str, door_data: dict) -> None:
        edge_type = door_data.get('type', 'door')
        is_secret = (edge_type == 'secret')
        transparent = edge_type in ('arch', 'portcullis')
        desc = door_data.get('desc', '').lower()
        locked = False
        if 'stuck' in desc:
            locked = True
        elif 'locked' in desc and 'unlocked' not in desc:
            locked = True
        elif door_data.get('locked', False):
            locked = True
        friendly = self._friendly_label(door_data)

        edge = NodeEdge(
            edge_id=f'{from_id}->{to_id}:{direction}:{abs(hash(door_data.get("desc", "")))%100000}',
            from_node_id=from_id, to_node_id=to_id,
            type=edge_type, direction=direction,
            label=friendly, description=door_data.get('desc', ''),
            locked=locked, secret=is_secret,
            trapped=door_data.get('trapped', False) or 'trapped' in desc,
            transparent=transparent,
            dc_open=door_data.get('dc_open'), dc_break=door_data.get('dc_break'),
            hp=door_data.get('hp'), trap_text=door_data.get('trap'),
            secret_text=door_data.get('secret'), hidden=is_secret,
            raw=door_data,
        )
        graph.edges[edge.edge_id] = edge
        rev = NodeEdge(
            edge_id=f'{to_id}->{from_id}:{self._opposite_direction(direction)}:{abs(hash(door_data.get("desc", "")))%100000}',
            from_node_id=to_id, to_node_id=from_id,
            type=edge_type, direction=self._opposite_direction(direction),
            label=friendly, description=door_data.get('desc', ''),
            locked=locked, secret=is_secret, trapped=edge.trapped,
            transparent=transparent,
            dc_open=door_data.get('dc_open'), dc_break=door_data.get('dc_break'),
            hp=door_data.get('hp'), trap_text=door_data.get('trap'),
            secret_text=door_data.get('secret'), hidden=is_secret,
            raw=door_data,
        )
        graph.edges[rev.edge_id] = rev

    def _create_edge(self, graph: NodeGraph, from_id: str, to_id: str, direction: str, label: str, edge_type: str = 'corridor_connector', transparent: bool = True) -> None:
        """Szigorúan egyirányú él létrehozása from_id -> to_id irányban."""
        edge = NodeEdge(
            edge_id=f'{from_id}->{to_id}:{direction}:{edge_type}',
            from_node_id=from_id, to_node_id=to_id,
            type=edge_type, direction=direction,
            label=label, description=label,
            locked=False, secret=False, trapped=False, transparent=transparent,
        )
        graph.edges[edge.edge_id] = edge

    def _create_double_edge(self, graph: NodeGraph, node_a: str, node_b: str, dir_a_to_b: str, label: str, edge_type: str = 'corridor_connector', transparent: bool = True) -> None:
        """Kétirányú kapcsolat létrehozása. Megadod az A-ból B-be vezető irányt, 
        a függvény pedig automatikusan kiszámítja és létrehozza a B-ből A-ba vezető ellentétes élet is."""
        # 1. Él: A -> B (a megadott irányba)
        self._create_edge(graph, node_a, node_b, dir_a_to_b, label, edge_type, transparent)
        
        # 2. Él: B -> A (az ellentétes irányba)
        dir_b_to_a = self._opposite_direction(dir_a_to_b)
        self._create_edge(graph, node_b, node_a, dir_b_to_a, label, edge_type, transparent)

    def _friendly_label(self, door_data: dict) -> str:
        desc = door_data.get('desc', '')
        door_type = door_data.get('type', 'door')
        material = "ajto"
        if 'wooden' in desc.lower():
            material = "faajto"
        elif 'stone' in desc.lower():
            material = "koajto"
        elif 'iron' in desc.lower():
            material = "vasajto"
        elif 'portcullis' in door_type:
            material = "felvonoracs"
        elif 'arch' in door_type:
            material = "boltiv"

        if 'secret' in door_type:
            return f"Titkos {material}"
        #if 'trapped' in door_type or 'trap' in desc.lower():
        #    return f"Csapdázott {material}"
        #if 'stuck' in desc.lower():
        #    return f"Beragadt {material}"
        #if 'locked' in door_type or 'locked' in desc.lower():
        #    return f"Zárt {material}"
        return f"{material.capitalize()}"

    def _corridor_description(self, level: int, cells_grid: List[List[int]], cells: List[Tuple[int, int]]) -> str:
        has_special = any(
            cells_grid[r][c] != 4 and has_bit(cells_grid[r][c], CELL_BITS["corridor"])
            for r, c in cells
        )
        return "A folyosón valami szokatlan látható." if has_special else ""

    def _direction_between_nodes(self, node_a: Node, node_b: Node) -> str:
        if node_a.center and node_b.center:
            return self._direction_between(
                int(node_a.center[0]), int(node_a.center[1]),
                int(node_b.center[0]), int(node_b.center[1])
            )
        return '?'

    def _direction_between(self, r1: int, c1: int, r2: int, c2: int) -> str:
        if r1 > r2: return 'north'
        if r1 < r2: return 'south'
        if c1 > c2: return 'west'
        return 'east'

    def _mark_entrance(self, graph: NodeGraph, manifest: dict) -> None:
        outside_id = f'{self.campaign_id}:outside'
        if outside_id in graph.nodes:
            graph.entrance_node_id = outside_id
        else:
            for node in sorted(graph.nodes.values(), key=lambda n: (n.level, n.node_id)):
                if node.type == 'room':
                    graph.entrance_node_id = node.node_id
                    return
            if graph.nodes:
                graph.entrance_node_id = next(iter(graph.nodes.keys()))

    @staticmethod
    def _opposite_direction(direction: str) -> str:
        mapping = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}
        return mapping.get(direction, direction)

    @staticmethod
    def _resolve_file(level_info: dict, manifest_dir: Path, key: str) -> Optional[Path]:
        dl = level_info.get('downloads') or {}
        if dl.get(key):
            p = Path(dl[key])
            return p if p.exists() else manifest_dir / p
        directory = Path(level_info.get('directory') or '')
        if not directory.is_absolute():
            directory = manifest_dir / directory
        if directory.exists():
            pattern = f'*.{key}'
            matches = sorted(directory.glob(pattern))
            return matches[0] if matches else None
        return None