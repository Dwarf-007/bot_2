from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from models.dungeon_graph_models import DungeonDoor, DungeonEdge, DungeonGraph, DungeonLevelAsset, DungeonRoom, DungeonStairMarker
from services.donjon.donjon_corridor_resolver import DonjonCorridorResolver, CorridorRegion
from collections import defaultdict
from services.donjon.donjon_tsv_parser import DonjonTsvParser

REVERSE_DIRECTION = {'north':'south','south':'north','east':'west','west':'east','up':'down','down':'up'}

class DonjonGraphBuilder:
    def __init__(self, campaign_id: str, dungeon_id: Optional[str]=None, title: Optional[str]=None, enable_tsv_corridors: bool=True) -> None:
        self.campaign_id=campaign_id; self.dungeon_id=dungeon_id or campaign_id; self.title=title or self.dungeon_id; self.enable_tsv_corridors=enable_tsv_corridors
        self._raw_level_data: Dict[int, Dict[str, Any]]={}; self._rooms_by_level: Dict[int, Dict[int, DungeonRoom]]={}; self._level_tsv: Dict[int, Path]={};
        self._corridor_regions_by_level: Dict[int, List[CorridorRegion]] = {}; self._perimeter_exits_by_level: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

    def build_from_manifest(self, manifest_file: str|Path) -> DungeonGraph:
        manifest_path=Path(manifest_file); manifest=self._read_json(manifest_path)
        campaign_id=str(manifest.get('campaign_id') or self.campaign_id); dungeon_id=self.dungeon_id or campaign_id; title=str(manifest.get('campaign_name') or self.title or dungeon_id)
        graph=DungeonGraph(campaign_id=campaign_id,dungeon_id=dungeon_id,title=title)
        graph.metadata['source_manifest']=str(manifest_path); graph.metadata['plan']=manifest.get('plan',{})
        for level_info in manifest.get('levels',[]):
            level=int(level_info.get('level')); json_file=self._resolve_level_json(level_info, manifest_path.parent)
            if not json_file:
                graph.metadata.setdefault('warnings',[]).append(f'Level {level}: no JSON export found'); continue
            data=self._read_json(json_file); self._raw_level_data[level]=data
            tsv_file=self._resolve_level_tsv(level_info, manifest_path.parent)
            if tsv_file: self._level_tsv[level]=tsv_file
            graph.levels.append(self._build_level_asset(level, level_info, json_file, tsv_file, data)); self._add_level(graph, level, data)
        if self.enable_tsv_corridors: self._add_tsv_corridor_edges(graph)
        self._add_explicit_stairs(graph); self._add_level_transition_edges_from_stairs(graph)
        self._deduplicate_edges(graph); self._ensure_room_exits(graph)
        self._mark_entrance(graph)
        graph.metadata.update({'room_count':len(graph.rooms),'edge_count':len(graph.edges),'stair_marker_count':len(graph.stairs),'level_count':len(graph.levels),'builder_version':'donjon_graph_builder_v3_tsv_corridors'})
        return graph

    def _mark_entrance(self, graph: DungeonGraph) -> None:
        plan = graph.metadata.get("plan") or {}
        direction = str(plan.get("default_direction") or "down").strip().lower()
        peripheral_egress = str(plan.get("settings", {}).get("peripheral_egress") or "No").strip()

        # A belépési szint meghatározása
        entry_level = self._find_entry_level(graph)

        # 1. Keresés lépcső alapján
        entry_stair_key = "up" if direction == "down" else "down"
        entry_stair = None
        for stair in graph.stairs:
            if stair.level == entry_level and stair.key == entry_stair_key:
                entry_stair = stair
                break

        if entry_stair:
            if entry_stair.room_id:
                # Lépcső szobában
                for room in graph.rooms:
                    if room.room_id == entry_stair.room_id:
                        room.is_entrance = True
                        break
                graph.entrance = {
                    "type": "room",
                    "level": entry_level,
                    "room_id": entry_stair.room_id,
                    "description": "Mögöttetek a lépcső, amin a dungeonbe érkeztetek."
                }
            elif entry_stair.corridor_region_id:
                # Lépcső folyosón
                graph.entrance = {
                    "type": "stair_in_corridor",
                    "level": entry_level,
                    "corridor_region_id": entry_stair.corridor_region_id,
                    "cell": {"row": entry_stair.row, "col": entry_stair.col},
                    "description": "A lépcső alján álltok, egy szűk folyosón."
                }
            else:
                # Fallback, ha a lépcsőt nem sikerült helyhez kötni
                pass

        # 2. Ha nincs lépcső, próbálkozunk perifériás kijárattal
        if not graph.entrance and peripheral_egress != "No":
            perimeter_exits = self._perimeter_exits_by_level.get(entry_level, [])
            if perimeter_exits:
                # Válasszuk az első kijáratot (vagy a legközelebbit a térkép széléhez)
                # Itt most egyszerűen az elsőt vesszük
                #exit_cell = perimeter_exits[0]
                for exit_cell in perimeter_exits:
                    # Megkeressük, melyik folyosórégió tartalmazza ezt a cellát
                    region_id = None
                    for region in self._corridor_regions_by_level.get(entry_level, []):
                        if exit_cell in region.cells:
                            region_id = region.region_id
                            break
                    if region_id:
                        graph.entrance = {
                            "type": "corridor_segment",
                            "level": entry_level,
                            "corridor_region_id": region_id,
                            "cell": {"row": exit_cell[0], "col": exit_cell[1]},
                            "description": "A dungeon bejárata egy szűk folyosón nyílik."
                        }
                        break

        # 3. Végső fallback: első szoba
        if not graph.entrance:
            level_rooms = [r for r in graph.rooms if r.level == entry_level]
            entrance_room = min(level_rooms, key=lambda r: r.room_number) if level_rooms else None
            if entrance_room:
                entrance_room.is_entrance = True
                graph.entrance = {
                    "type": "room",
                    "level": entry_level,
                    "room_id": entrance_room.room_id,
                    "description": "Beléptetek a terembe."
                }

    def _add_level(self, graph: DungeonGraph, level:int, data:Dict[str,Any]) -> None:
        lookup={}
        for raw in data.get('rooms') or []:
            if isinstance(raw,dict):
                room=self._parse_room(level, raw, graph.campaign_id, graph.dungeon_id); graph.rooms.append(room); lookup[room.room_number]=room
        self._rooms_by_level[level]=lookup
        for room in lookup.values():
            for door in room.doors:
                if not door.target_room_id: continue
                target_number=self._room_number_from_global_id(door.target_room_id)
                if target_number not in lookup:
                    graph.metadata.setdefault('warnings',[]).append(f'Level {level}: edge target missing {room.room_id} -> {door.target_room_id}'); continue
                graph.edges.append(self._door_edge(room, door, level, 'explicit_out_id'))

    def _add_tsv_corridor_edges(self, graph: DungeonGraph) -> None:
        all_reports=[]; all_unresolved=[]; added=0
        for level, tsv in self._level_tsv.items():
            grid = DonjonTsvParser.parse_file(tsv)
            # Perifériás kijáratok gyűjtése
            self._collect_perimeter_exits(level, grid)

            rooms=[r for r in graph.rooms if r.level==level]
            report=DonjonCorridorResolver(graph.campaign_id).resolve_level(level, tsv, rooms)
            regions = [CorridorRegion(**r) if isinstance(r, dict) else r for r in report.get('regions', [])]
            self._corridor_regions_by_level[level] = regions
            existing={(e.from_room_id,e.to_room_id,e.edge_type) for e in graph.edges}
            for raw_edge in report.get('edges',[]):
                key=(raw_edge['from_room_id'], raw_edge['to_room_id'], 'corridor')
                direct_key=(raw_edge['from_room_id'], raw_edge['to_room_id'], 'door')
                if key in existing or direct_key in existing: continue
                graph.edges.append(DungeonEdge(**raw_edge)); existing.add(key); added += 1
            all_reports.append({'level': level, 'tsv_file': str(tsv), 'regions': len(report.get('regions',[])), 'corridor_edges_raw': len(report.get('edges',[])), 'token_summary': report.get('token_summary',{})})
            all_unresolved.extend(report.get('unresolved_doors',[]))
        graph.metadata['tsv_corridor_reports']=all_reports; graph.metadata['tsv_corridor_edges_added']=added; graph.metadata['unresolved_corridor_doors_count']=len(all_unresolved); graph.metadata['unresolved_corridor_doors']=all_unresolved[:500]

    def _door_edge(self, room:DungeonRoom, door:DungeonDoor, level:int, confidence:str) -> DungeonEdge:
        return DungeonEdge(edge_id=self._edge_id(room.room_id,door.target_room_id or '',door.direction,door.description),from_room_id=room.room_id,to_room_id=door.target_room_id or '',level_from=level,level_to=level,edge_type='door',direction=door.direction,reverse_direction=REVERSE_DIRECTION.get(door.direction),door_type=door.door_type,description=door.description,locked=door.locked,secret=door.secret,trapped=door.trapped,dc_open=door.dc_open,dc_break=door.dc_break,hp=door.hp,trap_text=door.trap_text,secret_text=door.secret_text,confidence=confidence,raw=door.raw)

    def _parse_room(self, level:int, raw:Dict[str,Any], campaign_id:str, dungeon_id:str) -> DungeonRoom:
        n=int(raw.get('id')); contents=raw.get('contents') or {}; detail=contents.get('detail') or {}; summary=str(contents.get('summary') or raw.get('summary') or '').strip()
        monsters=self._listify(detail.get('monster')); traps=self._listify(detail.get('trap')); hidden=self._listify(detail.get('hidden_treasure')); features=self._listify(detail.get('room_features')); tricks=self._listify(detail.get('trick'))
        room=DungeonRoom(room_id=self.make_room_id(campaign_id,level,n),campaign_id=campaign_id,dungeon_id=dungeon_id,level=level,local_room_id=f'room_{n}',room_number=n,title=f'Level {level} Room #{n}',summary=summary,facts=self._build_facts(summary,features,monsters,traps,hidden,tricks),row=self._safe_int(raw.get('row')),col=self._safe_int(raw.get('col')),north=self._safe_int(raw.get('north')),south=self._safe_int(raw.get('south')),west=self._safe_int(raw.get('west')),east=self._safe_int(raw.get('east')),width=self._safe_int(raw.get('width')),height=self._safe_int(raw.get('height')),area=self._safe_int(raw.get('area')),shape=raw.get('shape'),size=raw.get('size'),polygon=self._safe_int(raw.get('polygon')),monsters=monsters,traps=traps,treasure=self._extract_treasure(monsters),hidden_treasure=hidden,features=features,tricks=tricks,raw=raw)
        room.doors=self._parse_doors(level, raw.get('doors') or {}, campaign_id); room.exits=self._build_exits_from_doors(room.doors); return room

    def _add_explicit_stairs(self, graph:DungeonGraph)->None:
        by_id={r.room_id:r for r in graph.rooms}
        for level,data in self._raw_level_data.items():
            for i,raw in enumerate(data.get('stairs') or [],1):
                if not isinstance(raw,dict): continue
                row=self._safe_int(raw.get('row')); col=self._safe_int(raw.get('col')); key=str(raw.get('key') or '').lower().strip()
                if row is None or col is None or key not in {'up','down'}: continue
                #room=self._find_room_for_cell(level,row,col)
                room, region = self._find_location_for_stair(level, row, col)
                marker=DungeonStairMarker(f'{graph.campaign_id}:L{level:02d}:stair_{key}_{i}',graph.campaign_id,graph.dungeon_id,level,key,raw.get('dir'),row,col,room.room_id if room else None,room.room_number if room else None,'explicit_json_inside_room' if room else 'explicit_json_no_room_match',region.region_id if region else None,raw)
                graph.stairs.append(marker)
                if room and room.room_id in by_id:
                    if key=='up': by_id[room.room_id].has_stair_up=True
                    if key=='down': by_id[room.room_id].has_stair_down=True
                    by_id[room.room_id].stair_markers.append(marker.marker_id)

    def _find_room_for_cell(self, level:int, row:int, col:int)->Optional[DungeonRoom]:
        cand=[]
        for room in self._rooms_by_level.get(level,{}).values():
            if None not in (room.north,room.south,room.west,room.east) and room.north <= row <= room.south and room.west <= col <= room.east:
                cand.append((room.area or 999999, room))
        if cand: return sorted(cand,key=lambda x:x[0])[0][1]
        #nearest=None; best=None
        #for room in self._rooms_by_level.get(level,{}).values():
        #    cr=((room.north or room.row or 0)+(room.south or room.row or 0))/2; cc=((room.west or room.col or 0)+(room.east or room.col or 0))/2; d=abs(cr-row)+abs(cc-col)
        #    if best is None or d<best: best=d; nearest=room
        #return nearest
        return None

    def _find_location_for_stair(self, level: int, row: int, col: int) -> Tuple[Optional[DungeonRoom], Optional[CorridorRegion]]:
        # 1. Szoba keresése (pontos illesztés)
        room = None
        cand = []
        for r in self._rooms_by_level.get(level, {}).values():
            if None not in (r.north, r.south, r.west, r.east) and r.north <= row <= r.south and r.west <= col <= r.east:
                cand.append((r.area or 999999, r))
        if cand:
            room = sorted(cand, key=lambda x: x[0])[0][1]
            return room, None  # talált szoba, folyosórégió nincs
    
        # 2. Ha nincs szoba, keresés a folyosórégiókban
        for region in self._corridor_regions_by_level.get(level, []):
            if (row, col) in region.cells:
                return None, region
    
        # 3. Ha semmi sem található
        return None, None

    def _add_level_transition_edges_from_stairs(self, graph:DungeonGraph)->None:
        d={}
        for s in graph.stairs: d.setdefault((s.level,s.key),[]).append(s)
        levels=sorted({a.level for a in graph.levels})
        for level in levels:
            if level+1 not in levels: continue
            down=self._preferred_stair(d.get((level,'down'),[])); up=self._preferred_stair(d.get((level+1,'up'),[]))
            if not down or not up or not down.room_id or not up.room_id: graph.metadata.setdefault('warnings',[]).append(f'Missing explicit stair link L{level:02d}->L{level+1:02d}'); continue
            graph.edges.append(DungeonEdge(self._edge_id(down.room_id,up.room_id,'down',f'stair {level}->{level+1}'),down.room_id,up.room_id,level,level+1,'stairs','down','up','stairs',f'Stairs down from level {level} to level {level+1}.',confidence='explicit_json_stairs',raw={'from_stair':down.to_dict(),'to_stair':up.to_dict()}))
            graph.edges.append(DungeonEdge(self._edge_id(up.room_id,down.room_id,'up',f'stair {level+1}->{level}'),up.room_id,down.room_id,level+1,level,'stairs','up','down','stairs',f'Stairs up from level {level+1} to level {level}.',confidence='explicit_json_stairs',raw={'from_stair':up.to_dict(),'to_stair':down.to_dict()}))

    def _parse_doors(self, level:int, raw_doors:Dict[str,Any], campaign_id:str)->List[DungeonDoor]:
        doors=[]
        for direction, entries in raw_doors.items():
            if not isinstance(entries,list): continue
            for e in entries:
                if not isinstance(e,dict): continue
                target=self._safe_int(e.get('out_id')); desc=str(e.get('desc') or '').strip(); typ=str(e.get('type') or 'door').strip()
                doors.append(DungeonDoor(str(direction),self.make_room_id(campaign_id,level,target) if target else None,f'room_{target}' if target else None,typ,desc,typ=='locked' or 'locked' in desc.lower(),typ=='secret' or bool(e.get('secret')),typ=='trapped' or bool(e.get('trap')) or 'trapped' in desc.lower(),self._extract_dc(desc,r'DC\s+(\d+)\s+to\s+open'),self._extract_dc(desc,r'DC\s+(\d+)\s+to\s+break'),self._extract_dc(desc,r'(\d+)\s*hp'),e.get('trap'),e.get('secret'),self._safe_int(e.get('row')),self._safe_int(e.get('col')),raw=e))
        return doors

    def _build_level_asset(self, level:int, info:Dict[str,Any], json_file:Path, tsv_file:Optional[Path], data:Dict[str,Any])->DungeonLevelAsset:
        dl=info.get('downloads') or {}; settings=data.get('settings') or {}
        return DungeonLevelAsset(level,str(json_file),dl.get('html_page') or info.get('html_file'),dl.get('map'),dl.get('players_map'),dl.get('pdf'),str(tsv_file) if tsv_file else dl.get('tsv'),info.get('directory'),self._safe_int(settings.get('n_rows')),self._safe_int(settings.get('n_cols')),self._safe_int(settings.get('cell_size')),data.get('cell_bit') or {})
    def _resolve_level_json(self, info:Dict[str,Any], manifest_dir:Path)->Optional[Path]: return self._resolve_file(info, manifest_dir, 'json', '*.json')
    def _resolve_level_tsv(self, info:Dict[str,Any], manifest_dir:Path)->Optional[Path]: return self._resolve_file(info, manifest_dir, 'tsv', '*.tsv')
    def _resolve_file(self, info:Dict[str,Any], manifest_dir:Path, key:str, pattern:str)->Optional[Path]:
        dl=info.get('downloads') or {}
        if dl.get(key):
            p=Path(dl[key]); return p if p.exists() else manifest_dir / p
        directory=Path(info.get('directory') or '')
        if not directory.is_absolute(): directory=manifest_dir/directory if not directory.exists() else directory
        if directory.exists():
            m=sorted(directory.glob(pattern)); return m[0] if m else None
        return None
    def _deduplicate_edges(self, graph:DungeonGraph)->None:
        seen=set(); out=[]
        for e in graph.edges:
            key=(e.from_room_id,e.to_room_id,e.direction,e.edge_type,e.confidence)
            if key in seen: continue
            seen.add(key); out.append(e)
        graph.edges=out
    def _ensure_room_exits(self, graph:DungeonGraph)->None:
        rooms={r.room_id:r for r in graph.rooms}
        for e in graph.edges:
            room=rooms.get(e.from_room_id)
            if not room or not e.direction: continue
            key=e.direction if e.edge_type!='corridor' else f'corridor_{e.direction or "exit"}'
            old=room.exits.get(key)
            if old is None: room.exits[key]=e.to_room_id
            elif isinstance(old,list):
                if e.to_room_id not in old: old.append(e.to_room_id)
            elif old!=e.to_room_id: room.exits[key]=[old,e.to_room_id]
    @staticmethod
    def make_room_id(campaign_id:str, level:int, room_number:int)->str: return f'{campaign_id}:L{int(level):02d}:R{int(room_number):03d}'
    @staticmethod
    def _room_number_from_global_id(room_id:str)->int:
        m=re.search(r':R(\d+)$', room_id); return int(m.group(1)) if m else -1
    @staticmethod
    def _edge_id(a:str,b:str,d:Optional[str],desc:str)->str: return f'{a}->{b}:{d or "unknown"}:{abs(hash(desc))%100000}'
    @staticmethod
    def _safe_int(v:Any)->Optional[int]:
        try: return None if v is None else int(v)
        except Exception: return None
    @staticmethod
    def _extract_dc(text:str, pattern:str)->Optional[int]:
        m=re.search(pattern,text or '',re.I); return int(m.group(1)) if m else None
    @staticmethod
    def _listify(v:Any)->List[str]:
        if v is None: return []
        if isinstance(v,list): return [str(x).strip() for x in v if str(x).strip() and str(x).strip()!='--']
        s=str(v).strip(); return [s] if s else []
    @staticmethod
    def _extract_treasure(monsters:List[str])->List[str]: return [x for x in monsters if x.lower().startswith('treasure:')]
    @staticmethod
    def _build_facts(summary,features,monsters,traps,hidden,tricks)->str:
        parts=[]
        if summary: parts.append(f'Summary: {summary}')
        if features: parts.append('Room features: '+' | '.join(features))
        if monsters: parts.append('Monsters/Treasure: '+' | '.join(monsters))
        if traps: parts.append('Traps: '+' | '.join(traps))
        if hidden: parts.append('Hidden treasure: '+' | '.join(hidden))
        if tricks: parts.append('Tricks: '+' | '.join(tricks))
        return '\n'.join(parts)
    @staticmethod
    def _build_exits_from_doors(doors:Iterable[DungeonDoor])->Dict[str,Any]:
        out={}
        for d in doors:
            if not d.target_room_id: continue
            old=out.get(d.direction)
            if old is None: out[d.direction]=d.target_room_id
            elif isinstance(old,list): old.append(d.target_room_id)
            else: out[d.direction]=[old,d.target_room_id]
        return out
    @staticmethod
    def _preferred_stair(stairs):
        wr=[s for s in stairs if s.room_id]; return wr[0] if wr else (stairs[0] if stairs else None)
    @staticmethod
    def _read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))

    def _find_entry_level(self, graph: DungeonGraph) -> int:
        """Visszaadja a belépési szint sorszámát (a legkisebb elérhető szint)."""
        levels = sorted({room.level for room in graph.rooms})
        return levels[0] if levels else 1

    def _collect_perimeter_exits(self, level: int, grid: DonjonTsvMap) -> None:
        exits = []
        # első és utolsó sor
        for col in range(grid.n_cols):
            for row in (0, grid.n_rows - 1):
                cell = grid.get(row, col)
                if cell and cell.walkable and cell.token == 'F':
                    exits.append((row, col))
        # első és utolsó oszlop (a sarkokat ne duplázzuk)
        for row in range(1, grid.n_rows - 1):
            for col in (0, grid.n_cols - 1):
                cell = grid.get(row, col)
                if cell and cell.walkable and cell.token == 'F':
                    exits.append((row, col))
        self._perimeter_exits_by_level[level] = exits
