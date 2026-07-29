from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class DungeonLevelAsset:
    level: int
    source_json: str
    source_html: Optional[str] = None
    map_image: Optional[str] = None
    players_map_image: Optional[str] = None
    pdf: Optional[str] = None
    tsv: Optional[str] = None
    directory: Optional[str] = None
    n_rows: Optional[int] = None
    n_cols: Optional[int] = None
    cell_size: Optional[int] = None
    cell_bit: Dict[str, int] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DungeonStairMarker:
    marker_id: str
    campaign_id: str
    dungeon_id: str
    level: int
    key: str
    direction: Optional[str]
    row: int
    col: int
    room_id: Optional[str]
    room_number: Optional[int]
    confidence: str = 'explicit_json'
    corridor_region_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DungeonDoor:
    direction: str
    target_room_id: Optional[str]
    target_local_room_id: Optional[str]
    door_type: str
    description: str
    locked: bool = False
    secret: bool = False
    trapped: bool = False
    dc_open: Optional[int] = None
    dc_break: Optional[int] = None
    hp: Optional[int] = None
    trap_text: Optional[str] = None
    secret_text: Optional[str] = None
    row: Optional[int] = None
    col: Optional[int] = None
    corridor_resolved_targets: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DungeonRoom:
    room_id: str
    campaign_id: str
    dungeon_id: str
    level: int
    local_room_id: str
    room_number: int
    title: str
    summary: str = ''
    facts: str = ''
    row: Optional[int] = None
    col: Optional[int] = None
    north: Optional[int] = None
    south: Optional[int] = None
    west: Optional[int] = None
    east: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    area: Optional[int] = None
    shape: Optional[str] = None
    size: Optional[str] = None
    polygon: Optional[int] = None
    has_stair_up: bool = False
    has_stair_down: bool = False
    is_entrance: bool = False
    stair_markers: List[str] = field(default_factory=list)
    doors: List[DungeonDoor] = field(default_factory=list)
    exits: Dict[str, Any] = field(default_factory=dict)
    monsters: List[str] = field(default_factory=list)
    traps: List[str] = field(default_factory=list)
    treasure: List[str] = field(default_factory=list)
    hidden_treasure: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    tricks: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['doors'] = [d.to_dict() if hasattr(d, 'to_dict') else d for d in self.doors]
        return data

@dataclass
class DungeonEdge:
    edge_id: str
    from_room_id: str
    to_room_id: str
    level_from: int
    level_to: int
    edge_type: str = 'door'
    direction: Optional[str] = None
    reverse_direction: Optional[str] = None
    door_type: Optional[str] = None
    description: str = ''
    locked: bool = False
    secret: bool = False
    trapped: bool = False
    dc_open: Optional[int] = None
    dc_break: Optional[int] = None
    hp: Optional[int] = None
    trap_text: Optional[str] = None
    secret_text: Optional[str] = None
    confidence: str = 'explicit'
    raw: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DungeonGraph:
    campaign_id: str
    dungeon_id: str
    title: str
    levels: List[DungeonLevelAsset] = field(default_factory=list)
    rooms: List[DungeonRoom] = field(default_factory=list)
    edges: List[DungeonEdge] = field(default_factory=list)
    stairs: List[DungeonStairMarker] = field(default_factory=list)
    entrance: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        return {
            'campaign_id': self.campaign_id,
            'dungeon_id': self.dungeon_id,
            'title': self.title,
            'levels': [x.to_dict() for x in self.levels],
            'rooms': [x.to_dict() for x in self.rooms],
            'edges': [x.to_dict() for x in self.edges],
            'stairs': [x.to_dict() for x in self.stairs],
            'entrance': self.entrance,
            'metadata': self.metadata,
        }
