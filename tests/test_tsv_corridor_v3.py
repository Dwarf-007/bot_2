from __future__ import annotations
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.donjon.donjon_graph_builder import DonjonGraphBuilder
from services.donjon.dungeon_bundle_exporter import DungeonBundleExporter

def main():
    root=Path('_tmp_v3'); shutil.rmtree(root, ignore_errors=True); (root/'level_01').mkdir(parents=True)
    data={'settings':{'cell_size':1},'stairs':[],'rooms':[None,{'id':'1','north':1,'south':3,'west':1,'east':3,'row':1,'col':1,'contents':{'summary':'A'},'doors':{'east':[{'row':2,'col':4,'desc':'Door','type':'door'}]}},{'id':'2','north':1,'south':3,'west':7,'east':9,'row':1,'col':7,'contents':{'summary':'B'},'doors':{'west':[{'row':2,'col':6,'desc':'Door','type':'door'}]}}]}
    jf=root/'level_01'/'l1.json'; jf.write_text(json.dumps(data),encoding='utf-8')
    # tab grid: room boxes are bypassed by corridor cells at cols 4,5,6
    tsv='\n'.join(['\t'.join(['']*11), '\t'.join(['','F','F','F','DL','F','DR','F','F','F','']), '\t'.join(['','F','F','F','DL','F','DR','F','F','F','']), '\t'.join(['','F','F','F','DL','F','DR','F','F','F',''])])
    tf=root/'level_01'/'l1.tsv'; tf.write_text(tsv,encoding='utf-8')
    mf=root/'manifest.json'; mf.write_text(json.dumps({'campaign_id':'t','levels':[{'level':1,'directory':str(root/'level_01'),'downloads':{'json':str(jf),'tsv':str(tf)}}]}),encoding='utf-8')
    g=DonjonGraphBuilder('t').build_from_manifest(mf)
    assert len([e for e in g.edges if e.edge_type=='corridor']) >= 2
    files=DungeonBundleExporter().export(g, root/'out')
    assert Path(files['navigation_index']).exists(); assert Path(files['corridor_graph']).exists()
    shutil.rmtree(root); print('OK v3 tsv corridor')
if __name__=='__main__': main()
