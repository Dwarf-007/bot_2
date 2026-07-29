from __future__ import annotations
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.visibility.visibility_graph_builder import VisibilityGraphBuilder


def main():
    root=Path('_tmp_visibility_test'); shutil.rmtree(root, ignore_errors=True); root.mkdir()
    (root/'level_01.tsv').write_text('\t'.join(['','','F','',''])+'\n'+'\t'.join(['','F','F','F',''])+'\n'+'\t'.join(['','','F','',''])+'\n', encoding='utf-8')
    room_raw={'west':1,'east':1,'north':1,'south':1}
    (root/'room_data.json').write_text(json.dumps({'rooms':[{'campaign_id':'t','room_id':'t:L01:R001','title':'R1','facts':'','raw':{'donjon':room_raw}}]}), encoding='utf-8')
    (root/'room_lookup.json').write_text(json.dumps({'t:L01:R001':'t:L01:R001'}), encoding='utf-8')
    (root/'navigation_index.json').write_text(json.dumps({'rooms':{}}), encoding='utf-8')
    (root/'dungeon_graph.json').write_text(json.dumps({'campaign_id':'t','levels':[{'level':1,'tsv_file':str(root/'level_01.tsv')}]}), encoding='utf-8')
    (root/'fog_manifest.json').write_text(json.dumps({'levels':[{'level':1,'tsv_file':str(root/'level_01.tsv')}]}), encoding='utf-8')
    g=VisibilityGraphBuilder(root).build_and_save()
    assert len(g['segments']) > 0
    shutil.rmtree(root)
    print('OK corridor visibility minimal')
if __name__=='__main__': main()
