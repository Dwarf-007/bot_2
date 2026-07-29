# services/dungeons/node_movement_engine.py
from __future__ import annotations
import random
from typing import Any, Dict, List, Optional

from models.node_graph_models import Node, NodeEdge, NodeGraph


class NodeMovementEngine:
    def __init__(self, graph: NodeGraph) -> None:
        self.graph = graph
        self.current_node_id: Optional[str] = None
        self.visited_nodes: List[str] = []

    def set_position(self, node_id: str) -> None:
        if node_id in self.graph.nodes:
            self.current_node_id = node_id
            if node_id not in self.visited_nodes:
                self.visited_nodes.append(node_id)

    def move(self, direction: str, choice: Optional[int] = None) -> Dict[str, Any]:
        if not self.current_node_id:
            return {"ok": False, "message": "Nincs beállított pozíció."}
        node = self.graph.nodes.get(self.current_node_id)
        if not node:
            return {"ok": False, "message": "Az aktuális csomópont nem található."}

        exits = self._visible_exits(node)
        matching = [e for e in exits if e.direction == direction]
        if not matching:
            return {"ok": False, "message": f"Nincs kijárat {direction} irányba."}
        edge = matching[0]

        if len(matching) > 1 and choice is None:
            options = [{"index": i+1, "label": e.label or e.description, "edge_id": e.edge_id} for i, e in enumerate(matching)]
            return {"ok": False, "message": f"Több kijárat is van {direction} irányban. Válassz a számokkal: `!move {direction} <szám>`", "ambiguity": options}
        
        if choice is not None:
            if 1 <= choice <= len(matching):
                edge = matching[choice - 1]
            else:
                return {"ok": False, "message": f"Érvénytelen választás. 1 és {len(matching)} közötti számot adj meg."}
        else:
            edge = matching[0]
        
        # Ha az él zárt, ne engedjük át
        if edge.locked:
            return {"ok": False, "message": f"Az átjáró zárva van. ({edge.label})"}

        # Csapda automatikus aktiválása, ha az él csapdázott
        if edge.trapped:
            damage = self._trigger_trap(edge)
            look_result = self.look()  # a jelenlegi csomópont adatai
            look_result["message"] = f"Csapda aktiválódott! {damage} sebzést szenvedtél el."
            return look_result


        # Mozgás
        self.current_node_id = edge.to_node_id
        if edge.to_node_id not in self.visited_nodes:
            self.visited_nodes.append(edge.to_node_id)
        return self.look()

    def open(self, direction: str) -> Dict[str, Any]:
        """Megpróbál kinyitni egy zárt ajtót az adott irányba."""
        if not self.current_node_id:
            return {"ok": False, "message": "Nincs beállított pozíció."}
        node = self.graph.nodes.get(self.current_node_id)
        if not node:
            return {"ok": False, "message": "Az aktuális csomópont nem található."}

        exits = self._exits(node)  # az összes kijárat, nem csak a láthatók
        matching = [e for e in exits if e.direction == direction]
        if not matching:
            return {"ok": False, "message": f"Nincs ajtó {direction} irányba."}
        edge = matching[0]

        if not edge.locked:
            return {"ok": True, "message": "Az ajtó már nyitva van."}

        if edge.dc_open:
            # Itt egyelőre automatikus sikeres nyitás, később lehet dobás
            pass

        # Az él és a fordított párjának kinyitása
        self._unlock_edge(edge)
        return {"ok": True, "message": f"Kinyitottad az ajtót: {edge.label}"}

    def look(self) -> Dict[str, Any]:
        if not self.current_node_id:
            return {"ok": False, "message": "Nincs beállított pozíció."}
        node = self.graph.nodes.get(self.current_node_id)
        if not node:
            return {"ok": False, "message": "Az aktuális csomópont nem található."}
        exits = self._visible_exits(node)
        formatted_exits = []
        for edge in exits:
            direction = edge.direction
            label = edge.label or f"{direction} felé"
            # Ha az aktuális csomópont folyosó, akkor pontosítsuk a pozíciót
            if node.type == 'corridor':
                pos = self._exit_position_on_corridor(node, edge)
                if pos:
                    direction = f"{direction} ({pos} rész)"
            formatted_exits.append({
                "edge_id": edge.edge_id,
                "direction": direction,
                "label": label,
                "description": edge.description,
                "type": edge.type,
                "target_node_id": edge.to_node_id,
                "transparent": edge.transparent,
                "locked": edge.locked,
                "trapped": edge.trapped,
            })
        return {
            "ok": True,
            "node": node.to_dict(),
            "exits": formatted_exits,
        }

    def search(self, search_type: str = "secret", dc: int = 15, roll: Optional[int] = None) -> Dict[str, Any]:
        if not self.current_node_id:
            return {"ok": False, "message": "Nincs beállított pozíció."}
        node = self.graph.nodes.get(self.current_node_id)
        if not node:
            return {"ok": False, "message": "Az aktuális csomópont nem található."}

        if search_type == "secret":
            return self._search_secret_doors(node, dc, roll)
        elif search_type == "trap":
            return self._search_traps(node, dc, roll)
        elif search_type == "treasure":
            return self._search_treasure(node, dc, roll)
        else:
            return {"ok": False, "message": "Ismeretlen keresési típus."}

    def _search_secret_doors(self, node: Node, dc: int, roll: Optional[int]) -> Dict[str, Any]:
        secret_edges = [e for e in self._exits(node) if e.secret and e.hidden]
        if not secret_edges:
            return {"ok": True, "message": "Nem találtál titkos átjárót."}
        if roll is None:
            import random
            roll = random.randint(1, 20)
        found = []
        for edge in secret_edges:
            dc_find = edge.dc_find or dc
            if roll >= dc_find:
                edge.hidden = False
                for e in self.graph.edges.values():
                    if e.from_node_id == edge.to_node_id and e.to_node_id == edge.from_node_id and e.type == edge.type:
                        e.hidden = False
                found.append(edge.edge_id)
        if found:
            return {"ok": True, "message": f"Titkos átjárót találtál: {', '.join(found)}!"}
        else:
            return {"ok": True, "message": "Nem sikerült felfedezned semmit."}

    def _search_traps(self, node: Node, dc: int, roll: Optional[int]) -> Dict[str, Any]:
        # Csapdák keresése a csomópont raw adataiból
        traps = node.raw.get('traps', [])
        if not traps:
            return {"ok": True, "message": "Nem találtál csapdát."}
        if roll is None:
            import random
            roll = random.randint(1, 20)
        found = []
        for trap in traps:
            # Feltételezzük, hogy a trap string, pl. "Falling Block: DC 10 to find, ..."
            # A DC-t ki kell nyerni belőle
            import re
            match = re.search(r'DC\s+(\d+)\s+to\s+find', trap)
            dc_find = int(match.group(1)) if match else dc
            if roll >= dc_find:
                found.append(trap)
        if found:
            return {"ok": True, "message": f"Csapdát találtál: {'; '.join(found)}"}
        else:
            return {"ok": True, "message": "Nem sikerült csapdát felfedezned."}

    def _search_treasure(self, node: Node, dc: int, roll: Optional[int]) -> Dict[str, Any]:
        # Kincsek keresése – a node.raw-ban lehetnek treasure és hidden_treasure mezők
        hidden = node.raw.get('hidden_treasure', [])
        if not hidden:
            return {"ok": True, "message": "Nem találtál rejtett kincset."}
        if roll is None:
            import random
            roll = random.randint(1, 20)
        found = []
        for item in hidden:
            # A hidden_treasure elemek stringek, pl. "Hidden (DC 20 to find) Trapped and Unlocked Strong Wooden Chest (20 hp)"
            import re
            match = re.search(r'DC\s+(\d+)\s+to\s+find', item)
            dc_find = int(match.group(1)) if match else dc
            if roll >= dc_find:
                found.append(item)
        if found:
            return {"ok": True, "message": f"Rejtett kincset találtál: {'; '.join(found)}"}
        else:
            return {"ok": True, "message": "Nem sikerült kincset felfedezned."}

    def _exits(self, node: Node) -> List[NodeEdge]:
        return [e for e in self.graph.edges.values() if e.from_node_id == node.node_id]

    def _visible_exits(self, node: Node) -> List[NodeEdge]:
        return [e for e in self._exits(node) if not (e.secret and e.hidden)]

    def _trigger_trap(self, edge: NodeEdge) -> int:
        """Aktivál egy csapdát és visszaadja a sebzést (vagy 0-t, ha nincs)."""
        # Egyszerű példa: 1d10 sebzés, ha van trap_text
        if edge.trap_text:
            damage = random.randint(1, 10)
            # A csapda egyszer használatos? Most marad aktív, de később kikapcsolhatjuk
            edge.trapped = False
            for e in self.graph.edges.values():
                if e.from_node_id == edge.to_node_id and e.to_node_id == edge.from_node_id and e.type == edge.type:
                    e.trapped = False
                    break   # ha egyszer használatos
            return damage
        return 0

    def _exit_position_on_corridor(self, corridor_node: 'Node', edge: 'NodeEdge') -> Optional[str]:
        """
        Meghatározza, hogy a kijárat a folyosó melyik részén található.
        Visszaadja: 'északi', 'déli', 'nyugati', 'keleti', 'középső', vagy None.
        """
        if not corridor_node.orientation or not corridor_node.cells:
            return None
        # A kijárat cellájának megtalálása (az élből és a cél csomópontból)
        # A legegyszerűbb: az él valamelyik végpontjának cellája, ami a folyosón van.
        # Mivel az él from_node_id-ja a folyosó, a folyosó egy cellája az él "kilépési pontja".
        # Keressük meg azt a cellát a folyosóban, amelyik szomszédos a cél csomópont valamelyik cellájával.
        target_node = self.graph.nodes.get(edge.to_node_id)
        if not target_node or not target_node.cells:
            return None
        for fc in corridor_node.cells:
            for tc in target_node.cells:
                if abs(fc[0] - tc[0]) + abs(fc[1] - tc[1]) == 1:
                    # fc a folyosó cellája, ahol a kijárat van
                    if corridor_node.orientation == 'horizontal':
                        # A folyosó vízszintes (sor állandó)
                        total_width = max(c for _, c in corridor_node.cells) - min(c for _, c in corridor_node.cells)
                        if total_width == 0:
                            return None
                        min_col = min(c for _, c in corridor_node.cells)
                        max_col = max(c for _, c in corridor_node.cells)
                        col = fc[1]
                        if col <= min_col + total_width * 0.25:
                            return 'nyugati'
                        elif col >= max_col - total_width * 0.25:
                            return 'keleti'
                        else:
                            return 'középső'
                    else:  # vertical
                        total_height = max(r for r, _ in corridor_node.cells) - min(r for r, _ in corridor_node.cells)
                        if total_height == 0:
                            return None
                        min_row = min(r for r, _ in corridor_node.cells)
                        max_row = max(r for r, _ in corridor_node.cells)
                        row = fc[0]
                        if row <= min_row + total_height * 0.25:
                            return 'északi'
                        elif row >= max_row - total_height * 0.25:
                            return 'déli'
                        else:
                            return 'középső'
        return None

    def _unlock_edge(self, edge: NodeEdge) -> None:
        """Kinyitja az adott élt és a fordított párját."""
        edge.locked = False
        # Megkeressük a fordított élt
        for e in self.graph.edges.values():
            if e.from_node_id == edge.to_node_id and e.to_node_id == edge.from_node_id and e.type == edge.type:
                e.locked = False
                break