
"""
SERVICES/RUNTIME_VISIBILITY_COMMAND_HANDLER.PY

Sprint 12.5 - Look State Persistence / Local Map Green-Path Hardening.

Fixes semantic issue observed in green-path smoke:
- `look` output reported visible cells,
- immediately following `map` said: "Nincs látható cella a térkép rendereléséhez.",
- later `full_map` worked after move/back persisted state.

Root cause candidate:
- VisibilityAwareMovementEngine.look(state) can return an updated serialized state in raw["state"],
  while the original `state` object passed to look may not contain refreshed visible_cells.
- Previous handler saved the original `state` object after look.

Fix:
- handle_look now persists state_service.state_from_raw(raw) when available.
"""

from __future__ import annotations

import copy
import inspect
from pathlib import Path
from typing import Any, Dict, Optional

from services.runtime_campaign_bundle_resolver import ResolvedCampaignBundle
from services.runtime_visibility_intents import RuntimeVisibilityIntent
from services.runtime_visibility_state_service import RuntimeVisibilityStateService
from services.visibility_runtime_formatter import VisibilityRuntimeFormatter


class RuntimeVisibilityCommandHandler:
    def __init__(self, state_service: RuntimeVisibilityStateService | None = None, formatter: VisibilityRuntimeFormatter | None = None) -> None:
        self.state_service = state_service or RuntimeVisibilityStateService()
        self.formatter = formatter or VisibilityRuntimeFormatter()

    def handle(self, *, bundle: ResolvedCampaignBundle, channel_id: str, player_id: str, intent: RuntimeVisibilityIntent) -> Dict[str, Any]:
        if intent.kind == "MAP":
            return self.handle_map(bundle=bundle, channel_id=channel_id, intent=intent)
        engine = self.create_engine(bundle)
        state = self.state_service.load_or_init_state(bundle, channel_id, player_id)
        if intent.kind == "LOOK":
            return self.handle_look(bundle=bundle, channel_id=channel_id, engine=engine, state=state)
        if intent.kind == "MOVE":
            if intent.direction == "back":
                return self.handle_back(bundle=bundle, channel_id=channel_id, engine=engine, state=state)
            return self.handle_move(bundle=bundle, channel_id=channel_id, engine=engine, state=state, intent=intent)
        if intent.kind == "SEARCH_SECRET":
            return self.handle_search_secret(bundle=bundle, channel_id=channel_id, state=state)
        return {"handled": False, "ok": False, "text": "", "raw": {}}

    def handle_map(self, *, bundle: ResolvedCampaignBundle, channel_id: str, intent: RuntimeVisibilityIntent) -> Dict[str, Any]:
        raw = self.render_map(bundle, channel_id, map_mode=getattr(intent, "map_mode", "local"))
        return {"handled": True, "ok": bool(raw.get("ok")), "text": self.format_map(raw), "raw": raw}

    def handle_look(self, *, bundle: ResolvedCampaignBundle, channel_id: str, engine: Any, state: Any) -> Dict[str, Any]:
        raw = engine.look(state)
        save_state = self.state_service.state_from_raw(raw) or state
        self.state_service.save_state(bundle, channel_id, save_state)
        return {"handled": True, "ok": bool(raw.get("ok", True)), "text": self.formatter.format_look(raw), "raw": raw}

    def handle_move(self, *, bundle: ResolvedCampaignBundle, channel_id: str, engine: Any, state: Any, intent: RuntimeVisibilityIntent) -> Dict[str, Any]:
        previous_position = self.clone_position(getattr(state, "current", None))
        before_history_len = len(getattr(state, "path_history", []) or [])
        raw = engine.move(state, intent.direction, intent.choice)
        save_state = self.state_service.state_from_raw(raw) or state
        if raw.get("ok"):
            self.ensure_previous_position_recorded(save_state, previous_position, before_history_len)
        self.state_service.save_state(bundle, channel_id, save_state)
        return {"handled": True, "ok": bool(raw.get("ok")), "text": self.formatter.format_move(raw), "raw": raw}

    def handle_back(self, *, bundle: ResolvedCampaignBundle, channel_id: str, engine: Any, state: Any) -> Dict[str, Any]:
        raw = self.backtrack(engine, state)
        save_state = self.state_service.state_from_raw(raw) or state
        self.state_service.save_state(bundle, channel_id, save_state)
        return {"handled": True, "ok": bool(raw.get("ok")), "text": self.format_backtrack(raw), "raw": raw}

    def handle_search_secret(self, *, bundle: ResolvedCampaignBundle, channel_id: str, state: Any) -> Dict[str, Any]:
        raw = self.search_secret(bundle, state)
        self.state_service.save_state(bundle, channel_id, state)
        return {"handled": True, "ok": bool(raw.get("ok", True)), "text": self.formatter.format_secret_search(raw), "raw": raw}

    def render_map(self, bundle: ResolvedCampaignBundle, channel_id: str, map_mode: str = "local") -> Dict[str, Any]:
        from services.runtime_visibility_map_service import RuntimeVisibilityMapService
        return RuntimeVisibilityMapService(bundle.bundle_dir, bundle.campaign_id).render_for_channel(channel_id, map_mode=map_mode).to_dict()

    def format_map(self, raw: Dict[str, Any]) -> str:
        if not raw.get("ok"):
            return str(raw.get("message") or "Nem sikerült elkészíteni a térképet.")
        explored = raw.get("explored_cells_count")
        newly = raw.get("newly_visible_cells_count")
        extra = ""
        if explored is not None:
            extra = f"\nFelfedezett cellák: {explored}"
            if newly is not None:
                extra += f", újonnan látható: {newly}"
        return (
            f"A látható térképrészlet elkészült.\n"
            f"Fájl: `{raw.get('output_file')}`\n"
            f"Szint: {raw.get('level')}, látható cellák: {raw.get('visible_cells_count')}"
            f"{extra}"
        )

    def create_engine(self, bundle: ResolvedCampaignBundle) -> Any:
        from services.movement.visibility_aware_movement_engine import VisibilityAwareMovementEngine
        candidates = [
            {"bundle_dir": str(bundle.bundle_dir), "campaign_id": bundle.campaign_id},
            {"bundle_dir": str(bundle.bundle_dir)},
            {"bundle_dir": bundle.bundle_dir},
            {},
        ]
        last_error: Optional[Exception] = None
        for kwargs in candidates:
            try:
                sig = inspect.signature(VisibilityAwareMovementEngine)
                accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
                return VisibilityAwareMovementEngine(**accepted)
            except Exception as exc:
                last_error = exc
                try:
                    if kwargs:
                        return VisibilityAwareMovementEngine(str(bundle.bundle_dir))
                except Exception as exc2:
                    last_error = exc2
        raise RuntimeError(f"Cannot construct VisibilityAwareMovementEngine: {last_error}")

    def clone_position(self, position: Any) -> Any:
        if position is None:
            return None
        try:
            if hasattr(position, "to_dict"):
                return self.position_from_any(position.to_dict())
            return copy.deepcopy(position)
        except Exception:
            return position

    def ensure_previous_position_recorded(self, state: Any, previous_position: Any, before_history_len: int) -> None:
        if previous_position is None:
            return
        self.state_service.migrate_state(state)
        if len(state.path_history) > before_history_len:
            return
        if self.same_position(previous_position, getattr(state, "current", None)):
            return
        state.path_history.append(previous_position)

    @staticmethod
    def same_position(a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        return (
            getattr(a, "node_id", None) == getattr(b, "node_id", None)
            and getattr(a, "node_type", None) == getattr(b, "node_type", None)
            and getattr(a, "room_id", None) == getattr(b, "room_id", None)
            and getattr(a, "segment_id", None) == getattr(b, "segment_id", None)
        )

    def backtrack(self, engine: Any, state: Any) -> Dict[str, Any]:
        self.state_service.migrate_state(state)
        history = getattr(state, "path_history", None)
        if not history:
            return {"ok": False, "message": "Nem egyértelmű, merre van vissza. Válassz a látható lehetőségek közül.", "look": engine.look(state).get("look") if hasattr(engine, "look") else None, "state": state.to_dict() if hasattr(state, "to_dict") else None}
        previous_position = self.position_from_any(history.pop())
        if previous_position is None:
            return {"ok": False, "message": "A visszalépési előzmény sérült.", "look": engine.look(state).get("look") if hasattr(engine, "look") else None, "state": state.to_dict() if hasattr(state, "to_dict") else None}
        state.current = previous_position
        self.mark_current_visited(state)
        look_raw = engine.look(state) if hasattr(engine, "look") else {"ok": True, "look": {}}
        return {"ok": True, "message": self.backtrack_message(previous_position), "look": look_raw.get("look") if isinstance(look_raw, dict) else None, "state": state.to_dict() if hasattr(state, "to_dict") else None}

    def position_from_any(self, value: Any) -> Any:
        from models.corridor_visibility_models import VisibilityPosition
        if isinstance(value, VisibilityPosition):
            return value
        if hasattr(value, "to_dict"):
            value = value.to_dict()
        if isinstance(value, dict):
            if hasattr(VisibilityPosition, "from_dict"):
                return VisibilityPosition.from_dict(value)
            return VisibilityPosition(node_id=value.get("node_id") or value.get("room_id") or value.get("segment_id") or "unknown", node_type=value.get("node_type") or ("room" if value.get("room_id") else "segment"), level=int(value.get("level") or 1), room_id=value.get("room_id"), segment_id=value.get("segment_id"), cell=value.get("cell"))
        return None

    def mark_current_visited(self, state: Any) -> None:
        current = getattr(state, "current", None)
        if not current:
            return
        room_id = getattr(current, "room_id", None)
        segment_id = getattr(current, "segment_id", None)
        if room_id and hasattr(state, "visited_rooms") and room_id not in state.visited_rooms:
            state.visited_rooms.append(room_id)
        if segment_id and hasattr(state, "visited_segments") and segment_id not in state.visited_segments:
            state.visited_segments.append(segment_id)
        try:
            from services.visibility.fog_of_war_policy import FogOfWarPolicy
            FogOfWarPolicy.mark_current_cell_visited(state)
        except Exception:
            pass

    @staticmethod
    def backtrack_message(position: Any) -> str:
        node_type = getattr(position, "node_type", "")
        if node_type == "room" or getattr(position, "room_id", None):
            return "Visszatértek a korábbi helyiség bejáratához."
        return "Visszaléptek az előző folyosószakaszra."

    def format_backtrack(self, raw: Dict[str, Any]) -> str:
        if not raw.get("ok"):
            msg = str(raw.get("message") or "Nem sikerült visszalépni.")
            look = raw.get("look")
            return f"{msg}\n\n{self.formatter.format_look({'look': look})}" if isinstance(look, dict) else msg
        msg = str(raw.get("message") or "Visszaléptetek.")
        look = raw.get("look")
        return f"{msg}\n\n{self.formatter.format_look({'look': look})}" if isinstance(look, dict) else msg

    def search_secret(self, bundle: ResolvedCampaignBundle, state: Any) -> Dict[str, Any]:
        current_room = getattr(getattr(state, "current", None), "room_id", None)
        if not current_room:
            return {
                "ok": True,
                "found": False,
                "message": "Jelenleg nem szobában álltok; titkos ajtót akkor tudtok megbízhatóan keresni, ha egy helyiségben vagy közvetlenül egy fal/ajtó mellett álltok.",
                "reason": "not_in_room",
            }
        try:
            from services.visibility.secret_door_discovery_engine import SecretDoorDiscoveryEngine
            from services.visibility.secret_discovery_state_store import SecretDiscoveryStateStore
        except Exception as exc:
            return {"ok": False, "found": False, "message": f"A titkos ajtó keresés modul nem elérhető: {exc}", "reason": "secret_module_import_failed"}
        store = SecretDiscoveryStateStore(bundle.bundle_dir / "secret_discovery_state.json")
        try:
            discovery = self._construct_secret_discovery_engine(SecretDoorDiscoveryEngine, bundle_dir=bundle.bundle_dir, store=store)
        except Exception as exc:
            return {"ok": False, "found": False, "message": f"A titkos ajtó keresés nem indítható ebben a bundle-ben: {exc}", "reason": "secret_engine_constructor_failed"}
        return self._call_secret_discovery_api(discovery, current_room=current_room, trait="secret")

    def _construct_secret_discovery_engine(self, engine_cls: Any, *, bundle_dir: str | Path, store: Any) -> Any:
        bundle_path = Path(bundle_dir)
        keyword_candidates = [
            {"bundle_dir": bundle_path, "state_store": store},
            {"bundle_dir": str(bundle_path), "state_store": store},
            {"bundle_dir": bundle_path, "store": store},
            {"bundle_dir": str(bundle_path), "store": store},
            {"bundle_dir": bundle_path},
            {"bundle_dir": str(bundle_path)},
            {"state_file": bundle_path / "secret_discovery_state.json"},
        ]
        positional_candidates = [(bundle_path, store), (str(bundle_path), store), (bundle_path,), (str(bundle_path),)]
        errors: list[str] = []
        for kwargs in keyword_candidates:
            try:
                accepted = self._accepted_kwargs(engine_cls, kwargs)
                if accepted:
                    return engine_cls(**accepted)
            except Exception as exc:
                errors.append(f"kwargs={sorted(kwargs.keys())}: {exc}")
        for args in positional_candidates:
            try:
                return engine_cls(*args)
            except Exception as exc:
                errors.append(f"args={len(args)}: {exc}")
        raise RuntimeError("; ".join(errors[-4:]) if errors else "no compatible constructor found")

    @staticmethod
    def _accepted_kwargs(callable_obj: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sig = inspect.signature(callable_obj)
        except Exception:
            return kwargs
        params = sig.parameters
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return kwargs
        return {k: v for k, v in kwargs.items() if k in params}

    def _call_secret_discovery_api(self, discovery: Any, *, current_room: str, trait: str = "secret") -> Dict[str, Any]:
        attempts = [
            ("search_room", {"room_id": current_room, "trait": trait, "auto_success": True}),
            ("search_room", {"room_id": current_room, "trait": trait, "roll_total": 99, "dc": 1}),
            ("search_room", {"room_id": current_room, "trait": trait}),
            ("reveal_room", {"room_id": current_room, "trait": trait}),
            ("search", {"room_id": current_room, "trait": trait, "auto_success": True}),
        ]
        type_errors: list[str] = []
        for name, kwargs in attempts:
            fn = getattr(discovery, name, None)
            if not callable(fn):
                continue
            try:
                result = fn(**kwargs)
                return self._normalise_secret_result(result)
            except TypeError as exc:
                type_errors.append(f"{name}: {exc}")
                continue
            except Exception as exc:
                return {"ok": False, "found": False, "message": f"A titkos ajtó keresés hibát jelzett: {exc}", "reason": "secret_search_exception"}
        return {"ok": False, "found": False, "message": "A SecretDoorDiscoveryEngine API nem ismert ebben a verzióban.", "reason": "secret_engine_api_unknown", "debug_type_errors": type_errors[-3:]}

    @staticmethod
    def _normalise_secret_result(result: Any) -> Dict[str, Any]:
        if hasattr(result, "to_dict"):
            data = result.to_dict()
        elif isinstance(result, dict):
            data = dict(result)
        else:
            data = {"ok": True, "found": bool(result)}
        data.setdefault("ok", True)
        data.setdefault("found", bool(data.get("found", False)))
        if not data.get("message"):
            data["message"] = "A keresés lefutott."
        return data
