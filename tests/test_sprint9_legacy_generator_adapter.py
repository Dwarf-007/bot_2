from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.generators.legacy_runtime_adapter import LegacyRuntimeGeneratorAdapter

class MockCampaignService:
    def __init__(self): self.calls=[]
    def ensure_campaign(self, campaign_id, campaign_name): self.calls.append((campaign_id,campaign_name))
class MockLocationRepo:
    def __init__(self): self.rooms=[]
    def upsert_room(self, room): self.rooms.append(room)
class MockRoomAliasService:
    def __init__(self): self.rooms=[]; self.lookup={}
    def ensure_room_aliases_from_room(self, campaign_id, room): self.rooms.append((campaign_id, room.get('room_id')))
    def import_lookup(self, campaign_id, lookup): self.lookup=lookup; return len(lookup)
class MockRagChunkRepo:
    def __init__(self): self.chunks=[]; self.deleted=[]; self.rebuilt=[]
    def delete_campaign_chunks(self, campaign_id): self.deleted.append(campaign_id)
    def upsert_chunk(self, chunk): self.chunks.append(chunk)
    def rebuild_fts(self, campaign_id=None): self.rebuilt.append(campaign_id)
class MockProgressService:
    def import_toc_entries(self, campaign_id, toc): return len(toc.get('entries', []))
    def ensure_scenes_from_rooms(self, campaign_id, rooms): return len(rooms)
class Runtime:
    def __init__(self):
        self.campaign_service=MockCampaignService(); self.location_repo=MockLocationRepo(); self.room_alias_service=MockRoomAliasService(); self.rag_chunk_repo=MockRagChunkRepo(); self.progress_service=MockProgressService()

def main():
    root=Path('_tmp_sprint9_bundle')
    if root.exists(): shutil.rmtree(root)
    root.mkdir()
    (root/'room_data.json').write_text(json.dumps({'rooms':[{'room_id':'r1','title':'Room 1'}]}), encoding='utf-8')
    (root/'room_lookup.json').write_text(json.dumps({'Room 1':'r1'}), encoding='utf-8')
    (root/'rag_index.json').write_text(json.dumps({'chunks':[{'chunk_id':'c1','text':'hello'}]}), encoding='utf-8')
    (root/'toc_index.json').write_text(json.dumps({'entries':[{'scene_id':'s1','title':'Scene 1'}]}), encoding='utf-8')
    rt=Runtime()
    result=LegacyRuntimeGeneratorAdapter(rt).import_bundle_dir('camp','Camp',root,clear_rag=True)
    assert result == {'rooms':1,'aliases':1,'chunks':1,'scenes':2}
    assert rt.location_repo.rooms[0]['campaign_id']=='camp'
    assert rt.rag_chunk_repo.deleted == ['camp']
    shutil.rmtree(root)
    print('OK Sprint9 legacy generator adapter')
if __name__=='__main__': main()
