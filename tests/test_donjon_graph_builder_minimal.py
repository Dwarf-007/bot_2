from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.donjon.donjon_graph_builder import DonjonGraphBuilder
from services.donjon.dungeon_bundle_exporter import DungeonBundleExporter


def main():
    root = Path('_tmp_donjon_graph_test')
    if root.exists(): shutil.rmtree(root)
    (root / 'level_01').mkdir(parents=True)
    sample = {
        'rooms': [None,
            {'id': '1', 'row': 1, 'col': 1, 'width': 50, 'height': 50, 'shape': 'square', 'contents': {'summary': 'Start'}, 'doors': {'north': [{'out_id': 2, 'desc': 'Unlocked Simple Wooden Door (10 hp)', 'type': 'door'}]}},
            {'id': '2', 'row': 1, 'col': 2, 'width': 50, 'height': 50, 'shape': 'square', 'contents': {'detail': {'monster': ['Goblin (cr 1/4); easy, 50 xp']}}, 'doors': {'south': [{'out_id': 1, 'desc': 'Unlocked Simple Wooden Door (10 hp)', 'type': 'door'}]}},
        ]
    }
    json_file = root / 'level_01' / 'sample.json'
    json_file.write_text(json.dumps(sample), encoding='utf-8')
    manifest = {'campaign_id': 'test', 'campaign_name': 'Test', 'levels': [{'level': 1, 'directory': str(root/'level_01'), 'downloads': {'json': str(json_file)}}]}
    manifest_file = root / 'manifest.json'
    manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
    graph = DonjonGraphBuilder('test').build_from_manifest(manifest_file)
    assert len(graph.rooms) == 2
    assert len(graph.edges) == 2
    out = root / 'bundle'
    files = DungeonBundleExporter().export(graph, out)
    assert Path(files['room_data']).exists()
    assert Path(files['rag_index']).exists()
    shutil.rmtree(root)
    print('OK donjon graph builder minimal')

if __name__ == '__main__': main()
