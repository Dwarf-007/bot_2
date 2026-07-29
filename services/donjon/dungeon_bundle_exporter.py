from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List
from models.dungeon_graph_models import DungeonGraph, DungeonRoom

class DungeonBundleExporter:
    def export(self, graph: DungeonGraph, output_dir: str|Path) -> Dict[str,str]:
        out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
        files={k:out/f'{k}.json' for k in ['dungeon_graph','room_data','room_lookup','rag_index','toc_index','map_geometry','stair_links','fog_manifest','navigation_index','corridor_graph','unresolved_doors']}
        self._write(files['dungeon_graph'], graph.to_dict())
        self._write(files['room_data'], {'rooms':[self._room_data(r) for r in graph.rooms]})
        self._write(files['room_lookup'], self._room_lookup(graph))
        self._write(files['rag_index'], {'chunks':[self._rag_chunk(r) for r in graph.rooms]})
        self._write(files['toc_index'], {'entries':[{'campaign_id':graph.campaign_id,'scene_id':f'level_{l:02d}','title':f'{graph.title} — Level {l}','order_index':l,'room_id':None} for l in sorted({r.level for r in graph.rooms})]})
        self._write(files['map_geometry'], self._map_geometry(graph))
        self._write(files['stair_links'], {'stairs':[s.to_dict() for s in graph.stairs], 'links':[e.to_dict() for e in graph.edges if e.edge_type=='stairs']})
        self._write(files['fog_manifest'], {'campaign_id':graph.campaign_id,'dungeon_id':graph.dungeon_id,'levels':[a.to_dict() for a in graph.levels],'geometry_file':'map_geometry.json'})
        self._write(files['navigation_index'], self._navigation_index(graph))
        self._write(files['corridor_graph'], {'edges':[e.to_dict() for e in graph.edges if e.edge_type=='corridor'], 'reports': graph.metadata.get('tsv_corridor_reports', [])})
        self._write(files['unresolved_doors'], {'items': graph.metadata.get('unresolved_corridor_doors', []), 'count': graph.metadata.get('unresolved_corridor_doors_count', 0)})
        return {k:str(v) for k,v in files.items()}
    def _room_data(self, r:DungeonRoom)->Dict[str,Any]:
        return {'campaign_id':r.campaign_id,'room_id':r.room_id,'title':r.title,'room_slug':self._slug(r.room_id),'facts':r.facts,'exits':r.exits,'monsters':[{'name':self._monster_name(x),'raw':x} for x in r.monsters if not x.lower().startswith('treasure:')],'traps':self._trap_entries(r),'treasure':r.treasure,'hidden_treasure':r.hidden_treasure,'has_stair_up':r.has_stair_up,'has_stair_down':r.has_stair_down,'is_entrance':r.is_entrance,'source_chunk_ids':[r.room_id],'raw':r.to_dict()}
    def _navigation_index(self, graph:DungeonGraph)->Dict[str,Any]:
        idx={r.room_id:{'room_id':r.room_id,'level':r.level,'neighbors':{},'all_neighbors':[]} for r in graph.rooms}
        for e in graph.edges:
            item=idx.get(e.from_room_id)
            if not item: continue
            key=e.direction or e.edge_type
            item['neighbors'].setdefault(key,[]).append({'room_id':e.to_room_id,'edge_type':e.edge_type,'confidence':e.confidence,'description':e.description})
            item['all_neighbors'].append(e.to_room_id)
        return {'campaign_id':graph.campaign_id,'dungeon_id':graph.dungeon_id,'rooms':idx}
    def _room_lookup(self, graph):
        d={}
        for r in graph.rooms:
            for k in [r.room_id,r.local_room_id,r.title,f'L{r.level:02d} R{r.room_number}',f'Level {r.level} Room {r.room_number}',f'room #{r.room_number} level {r.level}']: d[k]=r.room_id
        return d
    def _rag_chunk(self,r):
        return {'campaign_id':r.campaign_id,'chunk_id':r.room_id,'room_id':r.room_id,'title':r.title,'text':r.facts,'tags':['donjon','dungeon',f'level_{r.level}','room']+(['stair_up'] if r.has_stair_up else [])+(['stair_down'] if r.has_stair_down else []),'npc_names':[],'monster_names':[self._monster_name(x) for x in r.monsters if not x.lower().startswith('treasure:')],'trap_names':[self._trap_name(x) for x in r.traps],'keyword_hits':[]}
    def _map_geometry(self,graph): return {'campaign_id':graph.campaign_id,'dungeon_id':graph.dungeon_id,'levels':[a.to_dict() for a in graph.levels],'stairs':[s.to_dict() for s in graph.stairs],'rooms':[{'room_id':r.room_id,'level':r.level,'room_number':r.room_number,'row':r.row,'col':r.col,'north':r.north,'south':r.south,'west':r.west,'east':r.east,'width':r.width,'height':r.height,'shape':r.shape,'polygon':r.polygon,'has_stair_up':r.has_stair_up,'has_stair_down':r.has_stair_down} for r in graph.rooms]}
    def _trap_entries(self,r):
        out=[{'name':self._trap_name(x),'description':x,'trigger_on':['enter','search_failure'],'once':True} for x in r.traps]
        out += [{'name':self._trap_name(d.trap_text),'description':d.trap_text,'trigger_on':['open','forced_entry'],'once':True} for d in r.doors if d.trap_text]
        return out
    @staticmethod
    def _monster_name(x): return str(x).split(';',1)[0].strip() or 'Monster'
    @staticmethod
    def _trap_name(x): return str(x).split(':',1)[0].strip() or 'Trap'
    @staticmethod
    def _slug(x): return x.lower().replace(':','_').replace(' ','_')
    @staticmethod
    def _write(p:Path,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
