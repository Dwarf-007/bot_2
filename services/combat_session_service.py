"""
SERVICES/COMBAT_SESSION_SERVICE.PY
In-memory AI-DM combat helper-state lifecycle.

C4.1 extraction:
- Owns MonsterState and CombatState.
- Owns monster-state construction from room/encounter data.
- Owns active combat helper-state storage.
- Owns simple player AC and player-roll feedback storage.

Boundary:
- No Discord I/O.
- No Avrae dispatch.
- No LLM calls.
- No TurnOutput construction.

This service is intentionally still in-memory for C4.1 to preserve the existing
DMCombatService behavior. Repository-backed lifecycle can be introduced later.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from services.bestiary_service import BestiaryService


@dataclass
class MonsterState:
    """A single monster's non-authoritative AI-DM helper state."""

    name: str
    unique_id: str
    max_hp: int
    current_hp: int
    ac: int
    attack_bonus: int
    damage_dice: str
    xp: int = 0
    actions: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)


@dataclass
class CombatState:
    """Channel-scoped, non-authoritative AI-DM combat helper state."""

    channel_id: str
    monsters: Dict[str, MonsterState] = field(default_factory=dict)
    player_ac: Dict[str, int] = field(default_factory=dict)
    initiative_order: List[str] = field(default_factory=list)
    current_index: int = 0
    round_number: int = 1
    active: bool = False
    player_rolls: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CombatSessionStartResult:
    ok: bool
    state: Optional[CombatState] = None
    reason: str = ""


@dataclass(frozen=True)
class MonsterTurnCompletion:
    removed_monster_id: Optional[str] = None
    all_monsters_defeated: bool = False
    total_xp: int = 0


class CombatSessionService:
    """Owns the in-memory combat helper-state lifecycle."""

    def __init__(
        self,
        bestiary_service: BestiaryService | None = None,
        bestiary_path: str = "data/bestiary.json",
    ) -> None:
        self.bestiary_service = bestiary_service or BestiaryService(bestiary_path)
        self.combats: Dict[str, CombatState] = {}

    def get_monster_stats(self, name: str) -> Optional[Dict[str, Any]]:
        return self.bestiary_service.get_monster_stats(name)

    def start_combat_session(
        self,
        channel_id: str,
        monsters_data: List[Dict[str, Any]] | None,
    ) -> CombatSessionStartResult:
        channel_id = str(channel_id)
        existing = self.combats.get(channel_id)
        if existing and existing.active:
            return CombatSessionStartResult(False, existing, "active_combat_exists")

        monsters = self._build_monsters(monsters_data or [])
        if not monsters:
            return CombatSessionStartResult(False, None, "no_valid_monsters")

        state = CombatState(channel_id=channel_id, monsters=monsters, active=True)
        initiative: List[Tuple[int, str]] = []
        for uid, monster in monsters.items():
            init_roll = random.randint(1, 20) + (monster.attack_bonus // 2)
            initiative.append((init_roll, uid))
        initiative.sort(reverse=True)
        state.initiative_order = [uid for _, uid in initiative]
        self.combats[channel_id] = state
        return CombatSessionStartResult(True, state, "started")

    def get_current_monster_for_turn(self, channel_id: str) -> Optional[Tuple[str, MonsterState]]:
        state = self.get_combat_state(channel_id)
        if not state or not state.active or not state.initiative_order:
            return None

        if state.current_index >= len(state.initiative_order):
            state.round_number += 1
            state.current_index = 0

        uid = state.initiative_order[state.current_index]
        monster = state.monsters.get(uid)
        if not monster:
            return None
        return uid, monster

    def complete_monster_turn(self, channel_id: str, uid: str) -> MonsterTurnCompletion:
        state = self.get_combat_state(channel_id)
        if not state or not state.active:
            return MonsterTurnCompletion()

        state.current_index += 1
        removed_monster_id: Optional[str] = None
        total_xp = sum(monster.xp for monster in state.monsters.values())

        monster = state.monsters.get(uid)
        if monster and monster.current_hp <= 0:
            removed_monster_id = uid
            del state.monsters[uid]
            state.initiative_order = [item for item in state.initiative_order if item != uid]
            if state.current_index > len(state.initiative_order):
                state.current_index = len(state.initiative_order)

        all_dead = not state.monsters
        if all_dead:
            state.active = False

        return MonsterTurnCompletion(
            removed_monster_id=removed_monster_id,
            all_monsters_defeated=all_dead,
            total_xp=total_xp if all_dead else 0,
        )

    def set_player_ac(self, channel_id: str, player_id: str, ac: int) -> None:
        state = self.get_combat_state(channel_id)
        if state:
            state.player_ac[str(player_id)] = int(ac)

    def append_player_roll(self, channel_id: str, actor: str, formula: str, total: Any) -> None:
        state = self.get_combat_state(channel_id)
        if not state:
            return
        state.player_rolls.append({"actor": actor, "formula": formula, "total": total})

    def is_active(self, channel_id: str) -> bool:
        state = self.get_combat_state(channel_id)
        return state is not None and state.active

    def get_combat_state(self, channel_id: str) -> Optional[CombatState]:
        return self.combats.get(str(channel_id))

    def _build_monsters(self, monsters_data: List[Any]) -> Dict[str, MonsterState]:
        monsters: Dict[str, MonsterState] = {}
        for entry in self._normalize_monster_entries(monsters_data):
            raw_name = str(entry.get("name", "")).split("(cr")[0].strip()
            if not raw_name:
                continue
            stats = self.get_monster_stats(raw_name) or self._fallback_stats()
            try:
                count = int(entry.get("count", 1))
            except (TypeError, ValueError):
                count = 1

            for index in range(max(1, count)):
                unique_id = f"{raw_name} {index + 1}"
                hp = int((stats.get("hp") or {}).get("average", 10))
                ac_value = stats.get("ac", [10])
                ac = int(ac_value[0] if isinstance(ac_value, list) else ac_value or 10)
                attack_bonus = int(stats.get("attack_bonus", 2) or 2)
                damage = str(stats.get("damage", "1d6") or "1d6")
                xp = int(stats.get("xp", 10) or 10)
                monsters[unique_id] = MonsterState(
                    name=raw_name,
                    unique_id=unique_id,
                    max_hp=hp,
                    current_hp=hp,
                    ac=ac,
                    attack_bonus=attack_bonus,
                    damage_dice=damage,
                    xp=xp,
                    actions=self._extract_actions(stats),
                )
        return monsters

    def _normalize_monster_entries(self, monsters_data: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for entry in monsters_data or []:
            if isinstance(entry, str):
                text = entry.strip()
                if not text or text == "--" or text.lower().startswith("treasure:"):
                    continue
                normalized.append(self._parse_monster_string(text))
            elif isinstance(entry, dict):
                normalized.append(entry)
        return normalized

    @staticmethod
    def _parse_monster_string(text: str) -> Dict[str, Any]:
        raw_name = text.split("(cr")[0].strip()
        count = 1
        if "x" in text:
            parts = text.split("x", 1)
            try:
                count = int(parts[0].strip())
                raw_name = parts[1].split("(cr")[0].strip()
            except ValueError:
                pass
        return {"name": raw_name, "count": max(1, count)}

    @staticmethod
    def _extract_actions(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        for action in stats.get("action", []) or []:
            actions.append({
                "name": action.get("name", ""),
                "type": action.get("type", "melee"),
                "bonus": action.get("attack_bonus", 0),
                "damage": action.get("damage", "1d4"),
            })
        return actions

    @staticmethod
    def _fallback_stats() -> Dict[str, Any]:
        return {
            "hp": {"average": 10},
            "ac": [10],
            "attack_bonus": 2,
            "damage": "1d6",
            "xp": 10,
        }
