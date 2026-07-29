from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.visibility.player_look_sanitizer import PlayerLookSanitizer
from services.visibility.door_visibility_policy import DoorVisibilityPolicy


def main():
    policy = DoorVisibilityPolicy()
    labels = policy.build_labels(
        direction='east',
        entry_index=1,
        desc='Trapped and Unlocked Stone Door (60 hp)',
        target_room_id='tenebrous:L01:R099',
    )
    assert 'R099' not in labels.player_label
    assert 'csapdázott' not in labels.player_label.lower()
    assert 'tenebrous:L01:R099' in labels.dm_label

    sanitizer = PlayerLookSanitizer()
    look = {
        'visible_exits': [
            {
                'segment_id': 'tenebrous:L01:HV0058',
                'label': 'Keleti bejárat: kőajtó → tenebrous:L01:R099',
                'description': 'Keleti irányban egy kőajtó látható.',
                'dm_label': 'Keleti bejárat: csapdázott kőajtó → tenebrous:L01:R099',
                'hidden_traits': ['trapped'],
                'target_room_ids': ['tenebrous:L01:R099'],
            },
            {
                'direction': 'east',
                'room_id': 'tenebrous:L01:R099',
                'edge_type': 'door',
                'visible_now': True,
                'description': 'Trapped and Unlocked Stone Door (60 hp)',
            },
        ]
    }
    out = sanitizer.sanitize_look(look)
    assert len(out['visible_exits']) == 1
    item = out['visible_exits'][0]
    assert 'R099' not in item['label']
    assert 'dm_label' not in item
    assert 'hidden_traits' not in item
    print('OK player look sanitizer')

if __name__ == '__main__':
    main()
