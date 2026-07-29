from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.visibility.secret_door_discovery_engine import SecretDoorDiscoveryEngine


def main():
    root = Path('_tmp_secret_discovery_test')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    (root / 'corridor_visibility_graph.json').write_text(json.dumps({'segments': {}}), encoding='utf-8')
    (root / 'corridor_visibility_labels.json').write_text(json.dumps({
        'segments': {
            't:L01:HV0001': {'segment_id': 't:L01:HV0001', 'player_label': 'Északi bejárat: kőajtó', 'dm_label': 'Északi bejárat: rejtett kőajtó', 'hidden_traits': ['secret'], 'target_room_ids': ['t:L01:R002']}
        },
        'room_exits': {
            't:L01:R001': [{'segment_id': 't:L01:HV0001', 'room_id': 't:L01:R001', 'hidden_traits': ['secret'], 'player_label': 'Északi bejárat: kőajtó'}]
        }
    }), encoding='utf-8')
    engine = SecretDoorDiscoveryEngine(root)
    state = engine.init_state('t', overwrite=True)
    exits = [{'segment_id': 't:L01:HV0001', 'hidden_traits': ['secret'], 'label': 'Északi bejárat: kőajtó'}]
    assert engine.filter_player_visible_exits(exits, state) == []
    result = engine.search_room('t:L01:R001', state, roll_total=20, dc=15)
    assert result.ok and result.discovered
    assert engine.filter_player_visible_exits(exits, state) != []
    shutil.rmtree(root)
    print('OK secret discovery engine')

if __name__ == '__main__':
    main()
