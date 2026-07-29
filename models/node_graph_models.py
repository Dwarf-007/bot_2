# models/node_graph_models.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Node:
    node_id: str
    campaign_id: str
    level: int
    type: str  # room, corridor, stairs_landing, junction, dead_end, outside
    title: str
    description: str = ''
    cells: List[Tuple[int, int]] = field(default_factory=list)
    center: Optional[Tuple[float, float]] = None
    orientation: Optional[str] = None  # 'horizontal', 'vertical', vagy None (nem folyosó)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['cells'] = [[int(r), int(c)] for r, c in self.cells]
        if self.center:
            data['center'] = [self.center[0], self.center[1]]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        cells = [tuple(c) for c in data.get('cells', [])]
        center = tuple(data['center']) if data.get('center') else None
        return cls(
            node_id=data['node_id'],
            campaign_id=data['campaign_id'],
            level=data['level'],
            type=data['type'],
            title=data['title'],
            description=data.get('description', ''),
            cells=cells,
            center=center,
            orientation=data.get('orientation'),
            raw=data.get('raw', {}),
        )


@dataclass
class NodeEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    type: str  # door, arch, portcullis, stair, corridor_connector, secret_door, outside
    direction: str  # north, south, east, west, up, down
    label: str = ''
    description: str = ''
    locked: bool = False
    secret: bool = False
    trapped: bool = False
    transparent: bool = False
    dc_open: Optional[int] = None
    dc_break: Optional[int] = None
    dc_find: Optional[int] = None
    hp: Optional[int] = None
    trap_text: Optional[str] = None
    secret_text: Optional[str] = None
    hidden: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeEdge':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NodeGraph:
    campaign_id: str
    dungeon_id: str
    title: str
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: Dict[str, NodeEdge] = field(default_factory=dict)
    entrance_node_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'campaign_id': self.campaign_id,
            'dungeon_id': self.dungeon_id,
            'title': self.title,
            'nodes': {nid: node.to_dict() for nid, node in self.nodes.items()},
            'edges': {eid: edge.to_dict() for eid, edge in self.edges.items()},
            'entrance_node_id': self.entrance_node_id,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeGraph':
        graph = cls(
            campaign_id=data['campaign_id'],
            dungeon_id=data['dungeon_id'],
            title=data['title'],
            entrance_node_id=data.get('entrance_node_id'),
            metadata=data.get('metadata', {}),
        )
        for nid, ndata in data.get('nodes', {}).items():
            graph.nodes[nid] = Node.from_dict(ndata)
        for eid, edata in data.get('edges', {}).items():
            graph.edges[eid] = NodeEdge.from_dict(edata)
        return graph