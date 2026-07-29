from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.visibility.door_visibility_policy import DoorVisibilityPolicy


def main():
    policy = DoorVisibilityPolicy()
    labels = policy.build_labels(
        direction='east',
        entry_index=1,
        desc='Trapped and Unlocked Stone Door (60 hp)',
        door_type='',
        target_room_id='t:L01:R099',
    )
    assert 'csapdázott' not in labels.player_label.lower()
    assert 'zárt' not in labels.player_label.lower()
    assert 'kőajtó' in labels.player_label.lower()
    assert 'trapped' in labels.hidden_traits
    assert 'csapdázott' in labels.dm_label.lower()
    print('OK player safe labels')

if __name__ == '__main__':
    main()
