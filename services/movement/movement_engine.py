from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional

from models.movement_models import MovementOption, MovementResult, MovementState
from services.movement.navigation_repository import NavigationRepository

class MovementEngine:
    def __init__(self, repo: NavigationRepository) -> None:
        self.repo = repo

    def look(self, state: MovementState) -> MovementResult:
        state.ensure_current_visited()
        room = self.repo.get_room(state.current_room_id)
        options = self.options(state.current_room_id)
        if not room:
            return MovementResult(False, f'Current room not found: {state.current_room_id}', state, options=options)
        return MovementResult(True, self._format_look(room, options), state, room=room, options=options)

    def exits(self, state: MovementState) -> MovementResult:
        options = self.options(state.current_room_id)
        return MovementResult(True, self._format_exits(options), state, room=self.repo.get_room(state.current_room_id), options=options)

    def move(self, state: MovementState, direction: str, choice: Optional[int] = None) -> MovementResult:
        direction = self.repo.normalize_direction(direction)
        candidates = [self._option(direction, raw) for raw in self.repo.neighbors_by_direction(state.current_room_id, direction)]
        if not candidates:
            return MovementResult(False, f'Nincs kijárat ebbe az irányba: {direction}', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id))
        if len(candidates) > 1 and choice is None:
            return MovementResult(False, f'Több lehetséges kijárat van erre: {direction}. Adj meg választást: --choice N', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id), ambiguity=candidates)
        idx = 0 if choice is None else max(0, int(choice) - 1)
        if idx >= len(candidates):
            return MovementResult(False, f'Érvénytelen választás: {choice}. Lehetőségek száma: {len(candidates)}', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id), ambiguity=candidates)
        chosen = candidates[idx]
        previous = state.current_room_id
        state.path_history.append(previous)
        state.current_room_id = chosen.room_id
        state.ensure_current_visited()
        room = self.repo.get_room(state.current_room_id)
        return MovementResult(True, f'Mozgás: {previous} -> {state.current_room_id} ({direction})', state, room=room, options=self.options(state.current_room_id), chosen=chosen)

    def back(self, state: MovementState) -> MovementResult:
        if not state.path_history:
            return MovementResult(False, 'Nincs előző szoba a history-ban.', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id))
        previous = state.current_room_id
        state.current_room_id = state.path_history.pop()
        state.ensure_current_visited()
        return MovementResult(True, f'Visszalépés: {previous} -> {state.current_room_id}', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id))

    def goto(self, state: MovementState, room_ref: str) -> MovementResult:
        rid = self.repo.resolve_room_id(room_ref)
        if not rid:
            return MovementResult(False, f'Ismeretlen szoba: {room_ref}', state, room=self.repo.get_room(state.current_room_id), options=self.options(state.current_room_id))
        previous = state.current_room_id
        state.path_history.append(previous)
        state.current_room_id = rid
        state.ensure_current_visited()
        return MovementResult(True, f'Teleport/debug goto: {previous} -> {rid}', state, room=self.repo.get_room(rid), options=self.options(rid))

    def options(self, room_id: str) -> List[MovementOption]:
        raw = self.repo.all_options(room_id)
        result: List[MovementOption] = []
        for direction, items in raw.items():
            for item in items if isinstance(items, list) else [items]:
                result.append(self._option(direction, item))
        return result

    @staticmethod
    def _option(direction: str, item: Dict) -> MovementOption:
        return MovementOption(
            room_id=item.get('room_id'),
            direction=direction,
            edge_type=item.get('edge_type', ''),
            confidence=item.get('confidence', ''),
            description=item.get('description', ''),
            label=f"{direction} -> {item.get('room_id')} [{item.get('edge_type')}]",
        )

    def _format_look(self, room: Dict, options: List[MovementOption]) -> str:
        facts = room.get('facts') or room.get('title') or ''
        exits = self._format_exits(options)
        return f"{room.get('title')}\n\n{facts}\n\n{exits}"

    @staticmethod
    def _format_exits(options: List[MovementOption]) -> str:
        if not options:
            return 'Kijáratok: nincs ismert kijárat.'
        lines = ['Kijáratok:']
        for i, opt in enumerate(options, start=1):
            desc = f' — {opt.description}' if opt.description else ''
            lines.append(f'  {i}. {opt.direction}: {opt.room_id} ({opt.edge_type}, {opt.confidence}){desc}')
        return '\n'.join(lines)
