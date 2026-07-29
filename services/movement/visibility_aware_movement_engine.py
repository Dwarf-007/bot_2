from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.movement_models import MovementState
from services.movement.movement_engine import MovementEngine
from services.movement.navigation_repository import NavigationRepository

try:
    from services.visibility.visibility_engine import CorridorVisibilityEngine
    from services.visibility.visibility_state_store import VisibilityStateStore
except Exception:
    CorridorVisibilityEngine = None  # type: ignore
    VisibilityStateStore = None  # type: ignore

try:
    from services.visibility.visibility_label_service import VisibilityLabelService
except Exception:
    VisibilityLabelService = None  # type: ignore


class VisibilityAwareMovementEngine:
    ACTIONABLE_SEGMENT_TYPES = {"doorway", "corridor_segment", "stair", "dead_end", "corridor_node"}

    def __init__(self, bundle_dir: str | Path, state_file: str | Path | None = None) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.nav_repo = NavigationRepository(self.bundle_dir)
        self.base_engine = MovementEngine(self.nav_repo)
        self.visibility_available = (
            CorridorVisibilityEngine is not None
            and VisibilityStateStore is not None
            and (self.bundle_dir / "corridor_visibility_graph.json").exists()
        )
        self.visibility_engine = CorridorVisibilityEngine(self.bundle_dir) if self.visibility_available else None
        self.visibility_store = (
            VisibilityStateStore(state_file or (self.bundle_dir / "visibility_state.json"))
            if self.visibility_available else None
        )
        self.label_service = VisibilityLabelService(self.bundle_dir) if VisibilityLabelService is not None else None

    def init_visibility(self, campaign_id: str, start_room_id: str, overwrite: bool = False):
        if not self.visibility_available or not self.visibility_store:
            return None
        if self.visibility_store.path.exists() and not overwrite:
            state = self.visibility_store.load()
            if state:
                return state
        state = self.visibility_engine.init_state(campaign_id, start_room_id)  # type: ignore[union-attr]
        self.visibility_store.save(state)
        return state

    def _vstate(self, movement_state: MovementState):
        if not self.visibility_available or not self.visibility_store:
            return None
        state = self.visibility_store.load()
        if state:
            return state
        state = self.visibility_engine.init_state(movement_state.campaign_id, movement_state.current_room_id)  # type: ignore[union-attr]
        self.visibility_store.save(state)
        return state

    def look(self, movement_state: MovementState) -> Dict[str, Any]:
        if not self.visibility_available:
            return self.base_engine.look(movement_state).to_dict()
        state = self._vstate(movement_state)
        look = self.visibility_engine.look(state)  # type: ignore[union-attr]
        look = self._filtered_look(look)
        if self.label_service:
            look = self.label_service.enrich_look(look)
        self.visibility_store.save(state)  # type: ignore[union-attr]
        return {"ok": True, "visibility_mode": True, "look": look, "visibility_state": state.to_dict()}

    def exits(self, movement_state: MovementState) -> Dict[str, Any]:
        return self.look(movement_state)

    def move(self, movement_state: MovementState, direction: str, choice: Optional[int] = None) -> Dict[str, Any]:
        if not self.visibility_available:
            return self.base_engine.move(movement_state, direction, choice).to_dict()
        state = self._vstate(movement_state)
        if state.current.node_type == "room":
            return self._move_from_room(state, direction, choice)
        return self._move_from_segment(state, choice)

    def enter_room(self, movement_state: MovementState, room_id: str) -> Dict[str, Any]:
        if not self.visibility_available:
            return self.base_engine.goto(movement_state, room_id).to_dict()
        state = self._vstate(movement_state)
        out = self.visibility_engine.enter_room(state, room_id)  # type: ignore[union-attr]
        if out.get("ok"):
            movement_state.current_room_id = room_id
            movement_state.ensure_current_visited()
            self.visibility_store.save(state)  # type: ignore[union-attr]
        return out

    def back(self, movement_state: MovementState) -> Dict[str, Any]:
        if not self.visibility_available:
            return self.base_engine.back(movement_state).to_dict()
        state = self._vstate(movement_state)
        out = self.visibility_engine.back(state)  # type: ignore[union-attr]
        self.visibility_store.save(state)  # type: ignore[union-attr]
        if out.get("ok") and state.current.node_type == "room" and state.current.room_id:
            movement_state.current_room_id = state.current.room_id
        return out

    def _move_from_room(self, state, direction: str, choice: Optional[int]) -> Dict[str, Any]:
        norm = self._normalize_direction(direction)
        raw_look = self.visibility_engine.look(state)  # type: ignore[union-attr]
        raw_look = self._filtered_look(raw_look)
        if self.label_service:
            raw_look = self.label_service.enrich_look(raw_look)
        candidates = self._segment_candidates_for_direction(raw_look, norm)
        if not candidates:
            return {"ok": False, "message": f"Nincs közvetlenül látható folyosószakasz ebbe az irányba: {direction}", "visibility_candidates": raw_look.get("visible_exits", []), "visibility_state": state.to_dict()}
        if len(candidates) > 1 and choice is None:
            return {"ok": False, "message": f"Több látható folyosó/ajtó van erre: {direction}. Adj meg --choice N értéket.", "ambiguity": candidates, "visibility_state": state.to_dict()}
        idx = 0 if choice is None else max(0, int(choice) - 1)
        if idx >= len(candidates):
            return {"ok": False, "message": f"Érvénytelen választás: {choice}. Lehetőségek: {len(candidates)}", "ambiguity": candidates, "visibility_state": state.to_dict()}
        out = self.visibility_engine.move_to_segment(state, candidates[idx]["segment_id"])  # type: ignore[union-attr]
        if self.label_service and out.get('look'):
            out['look'] = self.label_service.enrich_look(out['look'])
        self.visibility_store.save(state)  # type: ignore[union-attr]
        return out

    def _move_from_segment(self, state, choice: Optional[int]) -> Dict[str, Any]:
        look = self.visibility_engine.look(state)  # type: ignore[union-attr]
        current = state.current.segment_id or state.current.node_id
        candidates = [sid for sid in look.get("visible_segments", []) if sid != current]
        if not candidates:
            return {"ok": False, "message": "A folyosó itt véget ér vagy nincs tovább látható szakasz.", "look": look, "visibility_state": state.to_dict()}
        if len(candidates) > 1 and choice is None:
            return {"ok": False, "message": "Több továbbvezető folyosószakasz látszik. Adj meg --choice N értéket.", "ambiguity": candidates, "look": look, "visibility_state": state.to_dict()}
        idx = 0 if choice is None else max(0, int(choice) - 1)
        if idx >= len(candidates):
            return {"ok": False, "message": f"Érvénytelen választás: {choice}. Lehetőségek: {len(candidates)}", "ambiguity": candidates, "look": look, "visibility_state": state.to_dict()}
        out = self.visibility_engine.move_to_segment(state, candidates[idx])  # type: ignore[union-attr]
        if self.label_service and out.get('look'):
            out['look'] = self.label_service.enrich_look(out['look'])
        self.visibility_store.save(state)  # type: ignore[union-attr]
        return out

    def _segment_candidates_for_direction(self, look: Dict[str, Any], norm_direction: str) -> List[Dict[str, Any]]:
        exits = self._filtered_visible_exits(look.get("visible_exits", []))
        if self.label_service:
            exits = [self.label_service.enrich_exit(x) for x in exits]
        segment_exits = [x for x in exits if x.get("segment_id")]
        hinted = [x for x in segment_exits if x.get("direction_hint") and self._normalize_direction(x.get("direction_hint")) == norm_direction]
        if hinted:
            return hinted
        return [x for x in segment_exits if not x.get("direction_hint")]

    def _filtered_look(self, look: Dict[str, Any]) -> Dict[str, Any]:
        if "visible_exits" in look:
            look = dict(look)
            look["visible_exits"] = self._filtered_visible_exits(look.get("visible_exits", []))
        return look

    def _filtered_visible_exits(self, exits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        seen = set()
        for item in exits:
            if item.get("room_id") and not item.get("segment_id"):
                if item.get("visible_now") is True:
                    key = ("room", item.get("room_id"), item.get("direction"))
                    if key not in seen:
                        seen.add(key)
                        filtered.append(item)
                continue
            sid = item.get("segment_id")
            if not sid:
                continue
            if item.get("segment_type") not in self.ACTIONABLE_SEGMENT_TYPES:
                continue
            key = ("segment", sid)
            if key in seen:
                continue
            seen.add(key)
            filtered.append(item)
        return filtered

    @staticmethod
    def _normalize_direction(value: Optional[str]) -> str:
        v = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down", "észak": "north", "eszak": "north", "dél": "south", "del": "south", "kelet": "east", "nyugat": "west", "fel": "up", "le": "down", "lefelé": "down", "lefele": "down"}.get(v, v)
