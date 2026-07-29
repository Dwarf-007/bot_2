# services/dungeons/dungeon_session.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.node_graph_models import NodeGraph
from services.dungeons.node_movement_engine import NodeMovementEngine


class DungeonSession:
    """Manages all state for an active dungeon campaign using the NodeGraph."""

    def __init__(self, bundle_dir: str | Path, campaign_id: str, channel_id: str = "", combat_service=None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.campaign_id = campaign_id
        self.channel_id = channel_id
        self.combat_service = combat_service

        # Új motor
        self.graph: Optional[NodeGraph] = None
        self.engine: Optional[NodeMovementEngine] = None

        # Combat state
        self.active_combat: bool = False
        self.monster_hp: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def init_new_game(self, start_node_id: str = None) -> Dict[str, Any]:
        """Betölti a node_graph.json-t és beállítja a kezdőpozíciót."""
        graph_path = self.bundle_dir / "node_graph.json"
        if not graph_path.exists():
            return {"ok": False, "message": "node_graph.json nem található a bundle-ben."}

        data = json.loads(graph_path.read_text(encoding="utf-8"))
        self.graph = NodeGraph.from_dict(data)
        self.engine = NodeMovementEngine(self.graph)

        # Kezdő csomópont meghatározása
        entrance_id = start_node_id or self.graph.entrance_node_id
        if not entrance_id:
            # Válasszuk az első room-ot
            for node_id, node in self.graph.nodes.items():
                if node.type == 'room':
                    entrance_id = node_id
                    break
        if not entrance_id:
            return {"ok": False, "message": "Nincs bejárati csomópont a gráfban."}

        self.engine.set_position(entrance_id)
        return self.look()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def move(self, direction: str, choice: Optional[int] = None) -> Dict[str, Any]:
        if not self.engine:
            return {"ok": False, "message": "Nincs aktív játék."}
        result = self.engine.move(direction, choice=choice)
        if result.get("ok"):
            node = self.graph.nodes.get(self.engine.current_node_id)
            if node and node.type == 'room':
                combat_output = self._check_combat_on_move(node)
                if combat_output:
                    result["combat_started"] = True
                    result["combat_narrative"] = combat_output.public_narrative
                    result["combat_commands"] = combat_output.avrae_commands
    
        return result

    def look(self) -> Dict[str, Any]:
        if not self.engine:
            return {"ok": False, "message": "Nincs aktív játék."}
        result = self.engine.look()
        if result.get("ok"):
            node = self.graph.nodes.get(self.engine.current_node_id)
            result["node_type"] = node.type if node else 'unknown'
            result["description"] = node.description if node else ''
            if node and node.type == 'room':
                raw = node.raw
                monsters = raw.get('monsters', []) or raw.get('contents', {}).get('detail', {}).get('monster', [])
                result["monsters"] = monsters
        return result

    def search(self, search_type: str = "secret", dc: int = 15, roll: Optional[int] = None) -> Dict[str, Any]:
        if not self.engine:
            return {"ok": False, "message": "Nincs aktív játék."}
        return self.engine.search(search_type=search_type, dc=dc, roll=roll)

    def rest(self, rest_type: str) -> Dict[str, Any]:
        if not self.engine:
            return {"ok": False, "message": "Nincs aktív játék."}
        node = self.graph.nodes.get(self.engine.current_node_id)
        if not node or node.type != 'room':
            return {"ok": False, "message": "Csak szobában pihenhetsz."}
        return {"ok": True, "message": f"Sikeres {rest_type} pihenő!"}

    def open_door(self, direction: str) -> Dict[str, Any]:
        if not self.engine:
            return {"ok": False, "message": "Nincs aktív játék."}
        return self.engine.open(direction)


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _check_combat_on_move(self, node) -> Optional[TurnOutput]:
        if not self.combat_service or not self.channel_id:
            return None
        raw = node.raw
        monsters = raw.get('monsters', []) or raw.get('contents', {}).get('detail', {}).get('monster', [])
        if monsters and not self.combat_service.is_active(self.channel_id):
            return self.combat_service.start_combat(
                channel_id=self.channel_id,
                monsters_data=monsters,
            )
        return None

    def render_map(self, output_file: Optional[str | Path] = None) -> Optional[str]:
        return None