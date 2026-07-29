from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.visibility.door_visibility_policy import DoorVisibilityPolicy
from services.donjon.raw_donjon import extract_donjon_raw

Cell = Tuple[int, int]


@dataclass
class DoorMetadata:
    room_id: str
    level: int
    direction: str
    entry_index: int
    row: int
    col: int
    desc: str
    door_type: str
    out_id: Optional[int] = None
    target_room_id: Optional[str] = None
    trap: Optional[str] = None
    secret: Optional[Any] = None
    segment_id: Optional[str] = None
    distance: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CorridorVisibilityDoorMetadataBinder:
    """Binds Donjon door metadata to corridor visibility segments with player-safe labels.

    Output contains both:
    - player_label / player_description: safe for players, no trap/secret spoilers
    - dm_label / dm_description: full truth for DM/runtime
    """

    def __init__(self, bundle_dir: str | Path, max_match_distance: int = 2) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.max_match_distance = max_match_distance
        self.policy = DoorVisibilityPolicy()
        self.room_data = self._read_json('room_data.json')
        self.visibility_graph = self._read_json('corridor_visibility_graph.json')
        self.rooms = {room['room_id']: room for room in self.room_data.get('rooms', []) if room.get('room_id')}
        self.segments = self.visibility_graph.get('segments', {})
        self.room_to_segments = self.visibility_graph.get('room_to_segments', {})

    def build(self) -> Dict[str, Any]:
        labels: Dict[str, Dict[str, Any]] = {}
        room_exits: Dict[str, List[Dict[str, Any]]] = {}
        unresolved: List[Dict[str, Any]] = []
        matched_doors = 0
        total_doors = 0
        hidden_trait_counts: Dict[str, int] = {}

        for room_id, room in sorted(self.rooms.items()):
            for door in self._extract_room_doors(room_id, room):
                total_doors += 1
                segment_id, dist = self._match_door_to_segment(room_id, (door.row, door.col))
                if not segment_id:
                    unresolved.append({
                        'room_id': room_id, 'level': door.level, 'direction': door.direction,
                        'entry_index': door.entry_index, 'row': door.row, 'col': door.col,
                        'desc': door.desc, 'reason': 'no_nearby_visibility_segment',
                    })
                    continue
                matched_doors += 1
                door.segment_id = segment_id
                door.distance = dist
                labels.setdefault(segment_id, self._empty_segment_label(segment_id))
                labels[segment_id]['door_metadata'].append(door.to_dict())

        for segment_id, entry in labels.items():
            self._infer_segment_targets(entry)
            exits = self._room_exit_entries_for_segment(entry)
            for ex in exits:
                room_exits.setdefault(ex['room_id'], []).append(ex)
                for trait in ex.get('hidden_traits', []):
                    hidden_trait_counts[trait] = hidden_trait_counts.get(trait, 0) + 1
            self._finalize_segment_label(entry, self.segments.get(segment_id, {}))

        for segment_id, segment in sorted(self.segments.items()):
            if segment_id not in labels:
                labels[segment_id] = self._default_segment_label(segment_id, segment)

        return {
            'schema_version': 'corridor_visibility_labels.player_safe.v1',
            'bundle_dir': str(self.bundle_dir),
            'visibility_policy': {
                'player_labels_hide': ['trapped', 'secret', 'hidden', 'concealed', 'invisible'],
                'dm_metadata_preserved': True,
            },
            'stats': {
                'rooms': len(self.rooms),
                'segments': len(self.segments),
                'doors_total': total_doors,
                'doors_matched': matched_doors,
                'doors_unresolved': len(unresolved),
                'rooms_with_labeled_exits': len(room_exits),
                'hidden_trait_counts': hidden_trait_counts,
            },
            'segments': labels,
            'room_exits': room_exits,
            'unresolved_doors': unresolved,
        }

    def build_and_save(self) -> Dict[str, Any]:
        data = self.build()
        (self.bundle_dir / 'corridor_visibility_labels.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        return data

    def _infer_segment_targets(self, entry: Dict[str, Any]) -> None:
        metadata = entry.get('door_metadata', [])
        rooms: List[str] = []
        for m in metadata:
            rid = m.get('room_id')
            if rid and rid not in rooms:
                rooms.append(rid)
        if len(rooms) >= 2:
            for m in metadata:
                if not m.get('target_room_id'):
                    for rid in rooms:
                        if rid != m.get('room_id'):
                            m['target_room_id'] = rid
                            break
        targets: List[str] = []
        for m in metadata:
            target = m.get('target_room_id')
            if target and target not in targets:
                targets.append(target)
        entry['target_room_ids'] = targets

    def _room_exit_entries_for_segment(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        exits: List[Dict[str, Any]] = []
        for m in entry.get('door_metadata', []):
            door = DoorMetadata(**m)
            exits.append(self._label_entry_for_door(door))
        return exits

    def _label_entry_for_door(self, door: DoorMetadata) -> Dict[str, Any]:
        labels = self.policy.build_labels(
            direction=door.direction,
            entry_index=door.entry_index,
            desc=door.desc,
            door_type=door.door_type,
            target_room_id=door.target_room_id,
            trap=door.trap,
            secret=door.secret,
        )
        return {
            'segment_id': door.segment_id,
            'room_id': door.room_id,
            'direction': door.direction,
            'entry_index': door.entry_index,
            'label': labels.player_label,
            'description': labels.player_description,
            'player_label': labels.player_label,
            'player_description': labels.player_description,
            'dm_label': labels.dm_label,
            'dm_description': labels.dm_description,
            'hidden_traits': labels.hidden_traits,
            'visible_traits': labels.visible_traits,
            'requires_detection': labels.requires_detection,
            'revealed_traits': [],
            'target_room_id': door.target_room_id,
            'door_type': door.door_type,
            'row': door.row,
            'col': door.col,
            'distance': door.distance,
        }

    def _extract_room_doors(self, room_id: str, room: Dict[str, Any]) -> List[DoorMetadata]:
        doors_obj = self._get_raw_doors(room)
        level = self._level_from_room_id(room_id)
        result: List[DoorMetadata] = []
        for direction, idx, entry in self._iter_door_entries(doors_obj):
            try:
                row = int(entry.get('row'))
                col = int(entry.get('col'))
            except Exception:
                continue
            out_id = entry.get('out_id')
            try:
                out_id_int = int(out_id) if out_id is not None else None
            except Exception:
                out_id_int = None
            target = self._make_room_id(room_id, out_id_int) if out_id_int is not None else None
            result.append(DoorMetadata(
                room_id=room_id,
                level=level,
                direction=direction,
                entry_index=idx,
                row=row,
                col=col,
                desc=str(entry.get('desc') or entry.get('description') or ''),
                door_type=str(entry.get('type') or ''),
                out_id=out_id_int,
                target_room_id=target,
                trap=entry.get('trap'),
                secret=entry.get('secret'),
            ))
        return result

    def _iter_door_entries(self, doors_obj: Any) -> List[Tuple[str, int, Dict[str, Any]]]:
        result: List[Tuple[str, int, Dict[str, Any]]] = []
        if isinstance(doors_obj, dict):
            for direction, entries in doors_obj.items():
                entries_list = entries if isinstance(entries, list) else [entries]
                for idx, entry in enumerate(entries_list, start=1):
                    if isinstance(entry, dict):
                        result.append((str(direction), idx, entry))
        elif isinstance(doors_obj, list):
            counters: Dict[str, int] = {}
            for entry in doors_obj:
                if not isinstance(entry, dict):
                    continue
                direction = str(entry.get('direction') or entry.get('dir') or entry.get('side') or entry.get('wall') or 'unknown')
                counters[direction] = counters.get(direction, 0) + 1
                result.append((direction, counters[direction], entry))
        return result

    def _get_raw_doors(self, room: Dict[str, Any]) -> Any:
        raw = extract_donjon_raw(room)
        return raw.get('doors') if isinstance(raw, dict) else None

    def _match_door_to_segment(self, room_id: str, cell: Cell) -> Tuple[Optional[str], Optional[int]]:
        best: Tuple[Optional[str], Optional[int]] = (None, None)
        for sid in self.room_to_segments.get(room_id, []):
            segment = self.segments.get(sid) or {}
            cells = [tuple(x) for x in segment.get('cells', [])]
            if not cells:
                continue
            dist = min(self._manhattan(cell, c) for c in cells)
            if dist <= self.max_match_distance and (best[1] is None or dist < best[1]):
                best = (sid, dist)
        return best

    def _empty_segment_label(self, segment_id: str) -> Dict[str, Any]:
        segment = self.segments.get(segment_id, {})
        return {
            'segment_id': segment_id,
            'segment_type': segment.get('segment_type'),
            'primary_label': None,
            'primary_description': None,
            'player_label': None,
            'player_description': None,
            'dm_label': None,
            'dm_description': None,
            'labels': [],
            'descriptions': [],
            'directions': [],
            'target_room_ids': [],
            'hidden_traits': [],
            'visible_traits': [],
            'requires_detection': False,
            'door_metadata': [],
        }

    def _default_segment_label(self, segment_id: str, segment: Dict[str, Any]) -> Dict[str, Any]:
        entry = self._empty_segment_label(segment_id)
        self._finalize_segment_label(entry, segment)
        return entry

    def _finalize_segment_label(self, entry: Dict[str, Any], segment: Dict[str, Any]) -> None:
        if entry.get('door_metadata'):
            exits = self._room_exit_entries_for_segment(entry)
            entry['labels'] = self._dedupe([e['label'] for e in exits])
            entry['descriptions'] = self._dedupe([e['description'] for e in exits])
            entry['directions'] = self._dedupe([e['direction'] for e in exits])
            entry['target_room_ids'] = self._dedupe([e['target_room_id'] for e in exits if e.get('target_room_id')])
            hidden: List[str] = []
            visible: List[str] = []
            for e in exits:
                hidden.extend(e.get('hidden_traits', []))
                visible.extend(e.get('visible_traits', []))
            entry['hidden_traits'] = self._dedupe(hidden)
            entry['visible_traits'] = self._dedupe(visible)
            entry['requires_detection'] = bool(entry['hidden_traits'])
            entry['primary_label'] = entry['labels'][0] if entry['labels'] else 'Ajtó vagy átjáró'
            entry['primary_description'] = entry['descriptions'][0] if entry['descriptions'] else entry['primary_label']
            entry['player_label'] = entry['primary_label']
            entry['player_description'] = entry['primary_description']
            entry['dm_label'] = exits[0]['dm_label'] if exits else entry['primary_label']
            entry['dm_description'] = exits[0]['dm_description'] if exits else entry['primary_description']
            return

        typ = segment.get('segment_type') or entry.get('segment_type') or 'segment'
        hint = segment.get('direction_hint')
        if typ == 'corridor_segment':
            direction = DoorVisibilityPolicy.direction_label_hu(hint) if hint else 'Ismeretlen irányú'
            label = f'{direction} folyosó'
            description = self._corridor_description_hu(hint, len(segment.get('cells') or []), segment)
        elif typ == 'junction':
            label = 'Folyosó-elágazás'; description = 'A folyosó itt több irányba ágazik.'
        elif typ == 'dead_end':
            label = 'Zsákutca'; description = 'A folyosó itt véget ér.'
        elif typ == 'stair':
            label = 'Lépcső'; description = 'Lépcső vezet tovább.'
        elif typ == 'doorway':
            label = 'Ajtó vagy átjáró'; description = 'Egy ajtó vagy átjáró látható.'
        else:
            label = str(typ); description = str(typ)
        entry['primary_label'] = label
        entry['primary_description'] = description
        entry['player_label'] = label
        entry['player_description'] = description
        entry['dm_label'] = label
        entry['dm_description'] = description

    @staticmethod
    def _corridor_description_hu(direction_hint: Optional[str], length: int, segment: Dict[str, Any]) -> str:
        direction = DoorVisibilityPolicy.direction_label_hu(direction_hint) if direction_hint else 'valamelyik irányba'
        if length >= 10:
            prefix = f'{direction} hosszabb folyosó vezet.'
        elif length >= 4:
            prefix = f'{direction} rövid folyosószakasz vezet.'
        else:
            prefix = f'{direction} keskeny átjáró látszik.'
        connected = len(segment.get('connected_segments') or [])
        if connected >= 3:
            prefix += ' A szakasz végén elágazás sejthető.'
        elif connected == 1:
            prefix += ' A szakasz végén valószínűleg zsákutca vagy ajtó van.'
        else:
            prefix += ' A kanyar vagy csatlakozás után nem látsz tovább.'
        return prefix

    @staticmethod
    def _dedupe(values: List[Any]) -> List[Any]:
        out: List[Any] = []
        for value in values:
            if value not in out:
                out.append(value)
        return out

    @staticmethod
    def _manhattan(a: Cell, b: Cell) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _level_from_room_id(room_id: str) -> int:
        m = re.search(r':L(\d+):', room_id)
        return int(m.group(1)) if m else 1

    @staticmethod
    def _make_room_id(current_room_id: str, out_id: int) -> str:
        return f"{current_room_id.rsplit(':R', 1)[0]}:R{out_id:03d}"

    def _read_json(self, name: str) -> Dict[str, Any]:
        path = self.bundle_dir / name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
