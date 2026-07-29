from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.donjon.donjon_graph_builder import DonjonGraphBuilder
from services.donjon.dungeon_bundle_exporter import DungeonBundleExporter


def main():
    root = Path('_tmp_donjon_graph_test_v2')
    if root.exists(): shutil.rmtree(root)
    (root / 'level_01').mkdir(parents=True)
    (root / 'level_02').mkdir(parents=True)
    l1 = {'cell_bit': {'stair_down': 4194304, 'stair_up': 8388608}, 'settings': {'n_rows': 20, 'n_cols': 20, 'cell_size': 14}, 'stairs': [{'row': 5, 'col': 5, 'key': 'down', 'dir': 'south'}], 'rooms': [None, {'id': '1', 'north': 1, 'south': 10, 'west': 1, 'east': 10, 'row': 1, 'col': 1, 'contents': {'summary': 'Start'}, 'doors': {}}]}
    l2 = {'cell_bit': {'stair_down': 4194304, 'stair_up': 8388608}, 'settings': {'n_rows': 20, 'n_cols': 20, 'cell_size': 14}, 'stairs': [{'row': 6, 'col': 6, 'key': 'up', 'dir': 'north'}], 'rooms': [None, {'id': '1', 'north': 1, 'south': 10, 'west': 1, 'east': 10, 'row': 1, 'col': 1, 'contents': {'summary': 'Next'}, 'doors': {}}]}
    j1 = root/'level_01'/'l1.json'; j2 = root/'level_02'/'l2.json'
    j1.write_text(json.dumps(l1), encoding='utf-8'); j2.write_text(json.dumps(l2), encoding='utf-8')
    manifest = {'campaign_id': 'test', 'campaign_name': 'Test', 'levels': [{'level': 1, 'directory': str(root/'level_01'), 'downloads': {'json': str(j1)}}, {'level': 2, 'directory': str(root/'level_02'), 'downloads': {'json': str(j2)}}]}
    mf = root/'manifest.json'; mf.write_text(json.dumps(manifest), encoding='utf-8')
    graph = DonjonGraphBuilder('test').build_from_manifest(mf)
    assert len(graph.stairs) == 2
    assert len([e for e in graph.edges if e.edge_type == 'stairs']) == 2
    assert any(room.has_stair_down for room in graph.rooms)
    assert any(room.has_stair_up for room in graph.rooms)
    files = DungeonBundleExporter().export(graph, root/'bundle')
    assert Path(files['stair_links']).exists()
    assert Path(files['fog_manifest']).exists()
    shutil.rmtree(root)
    print('OK donjon graph builder v2 stairs')

if __name__ == '__main__': main()
