from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.movement_models import MovementState
from services.movement.navigation_repository import NavigationRepository
from services.movement.movement_engine import MovementEngine


def main():
    root = Path('_tmp_movement_test')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    (root/'navigation_index.json').write_text(json.dumps({'rooms': {
        't:L01:R001': {'room_id':'t:L01:R001','level':1,'neighbors': {'east': [{'room_id':'t:L01:R002','edge_type':'door','confidence':'explicit','description':'door'}]}, 'all_neighbors':['t:L01:R002']},
        't:L01:R002': {'room_id':'t:L01:R002','level':1,'neighbors': {'west': [{'room_id':'t:L01:R001','edge_type':'door','confidence':'explicit','description':'door'}]}, 'all_neighbors':['t:L01:R001']},
    }}), encoding='utf-8')
    (root/'room_data.json').write_text(json.dumps({'rooms':[{'campaign_id':'t','room_id':'t:L01:R001','title':'Room 1','facts':'Start','exits':{}},{'campaign_id':'t','room_id':'t:L01:R002','title':'Room 2','facts':'Next','exits':{}}]}), encoding='utf-8')
    (root/'room_lookup.json').write_text(json.dumps({'room 1':'t:L01:R001','room 2':'t:L01:R002'}), encoding='utf-8')
    repo=NavigationRepository(root); engine=MovementEngine(repo); state=MovementState('t','t:L01:R001')
    res=engine.move(state,'east')
    assert res.ok and res.state.current_room_id == 't:L01:R002'
    res=engine.back(state)
    assert res.ok and res.state.current_room_id == 't:L01:R001'
    shutil.rmtree(root)
    print('OK movement engine minimal')

if __name__ == '__main__': main()
