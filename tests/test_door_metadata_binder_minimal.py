from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.visibility.door_metadata_binder import CorridorVisibilityDoorMetadataBinder


def main():
    root = Path('_tmp_label_binder_test')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    room_id = 't:L01:R001'
    seg_id = 't:L01:HV0001'
    (root / 'room_data.json').write_text(json.dumps({
        'rooms': [{
            'room_id': room_id,
            'raw': {'donjon': {'doors': {'east': [{'row': 5, 'col': 6, 'desc': 'Locked Stone Door (DC 15 to open)', 'type': 'locked', 'out_id': 2}]}}}
        }]
    }), encoding='utf-8')
    (root / 'corridor_visibility_graph.json').write_text(json.dumps({
        'segments': {seg_id: {'segment_id': seg_id, 'segment_type': 'doorway', 'cells': [[5, 6]], 'connected_segments': [], 'adjacent_rooms': [room_id]}},
        'room_to_segments': {room_id: [seg_id]},
    }), encoding='utf-8')
    data = CorridorVisibilityDoorMetadataBinder(root).build_and_save()
    assert data['stats']['doors_total'] == 1
    assert data['stats']['doors_matched'] == 1
    assert data['segments'][seg_id]['primary_label'].startswith('Keleti')
    shutil.rmtree(root)
    print('OK door metadata binder minimal')

if __name__ == '__main__':
    main()
