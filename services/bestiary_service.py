"""services/bestiary_service.py
Provides a local bestiary lookup facade.

F1.5 compatibility migration:
- Keeps the existing BestiaryService public API: get_monster_stats(name).
- Keeps legacy data/bestiary.json loading behavior.
- Optionally supports the new F1 compendium stack:
  - FiveEToolsDataSource
  - CompendiumIndexService
  - SourcePolicy

This allows combat runtime code to keep using BestiaryService while the project
moves toward the canonical compendium layer.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType, CompendiumQuery
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.source_policy import SourcePolicy


class BestiaryService:
    """Monster lookup compatibility facade.

    Legacy mode:
        BestiaryService(path="data/bestiary.json")

    Compendium-backed mode:
        BestiaryService(compendium_index=index)

    Raw 5etools compendium mode:
        BestiaryService(compendium_raw_root="data/compendium/fiveetools/raw")
    """

    def __init__(
        self,
        path: str = "data/bestiary.json",
        compendium_index: CompendiumIndexService | None = None,
        source_policy: SourcePolicy | None = None,
        prefer_compendium: bool = True,
        compendium_raw_root: str | Path | None = None,
    ) -> None:
        self.path = Path(path)
        self._bestiary: Dict[str, Any] = {}
        self.source_policy = source_policy
        self.prefer_compendium = bool(prefer_compendium)
        self.compendium_index = compendium_index

        if self.compendium_index is None and compendium_raw_root is not None:
            data_source = FiveEToolsDataSource(compendium_raw_root)
            entries = data_source.load_entries(entry_types=[CompendiumEntryType.MONSTER])
            self.compendium_index = CompendiumIndexService(entries)

        self._load_bestiary()

    def _load_bestiary(self) -> None:
        if not self.path.exists():
            self._bestiary = {}
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            self._bestiary = {}
            return

        monsters = raw.get("monster") if isinstance(raw, dict) else None
        if monsters is None and isinstance(raw, list):
            monsters = raw
        if monsters is None:
            monsters = []

        normalized: Dict[str, Any] = {}
        for monster in monsters:
            if not isinstance(monster, dict):
                continue
            name = str(monster.get("name") or monster.get("monster_name") or "").strip()
            if not name:
                continue
            normalized[name.lower()] = monster

        self._bestiary = normalized

    def get_monster_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Return monster stats by name.

        Preferred behavior after F1.5:
        1. Try compendium monster lookup when configured and prefer_compendium=True.
        2. Fall back to legacy data/bestiary.json lookup.
        3. If prefer_compendium=False, use legacy first, then compendium.
        """
        key = str(name).strip().lower()
        if not key:
            return None

        if self.prefer_compendium:
            compendium_result = self._get_monster_stats_from_compendium(name)
            if compendium_result:
                return compendium_result
            return self._get_monster_stats_from_legacy(key)

        legacy_result = self._get_monster_stats_from_legacy(key)
        if legacy_result:
            return legacy_result
        return self._get_monster_stats_from_compendium(name)

    def _get_monster_stats_from_legacy(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self._bestiary:
            return self._bestiary[key]

        # Partial match fallback: first bestiary entry whose name contains the query.
        # This is kept for compatibility with the pre-F1 BestiaryService behavior.
        for monster_name, monster_data in self._bestiary.items():
            if key in monster_name:
                return monster_data

        return None

    def _get_monster_stats_from_compendium(self, name: str) -> Optional[Dict[str, Any]]:
        if self.compendium_index is None:
            return None

        query = CompendiumQuery(
            text=str(name),
            entry_types=[CompendiumEntryType.MONSTER],
            limit=1,
        )
        results = self.compendium_index.search(query, source_policy=self.source_policy)
        if not results:
            return None
        return self._entry_to_monster_stats(results[0].entry)

    def _entry_to_monster_stats(self, entry: CompendiumEntry) -> Dict[str, Any]:
        raw = dict(entry.raw or {})
        name = str(raw.get("name") or raw.get("monster_name") or entry.name).strip()

        # If this entry already looks like the legacy AI-DM normalized shape,
        # preserve it with only minimal metadata enrichment.
        if self._looks_like_normalized_monster(raw):
            result = dict(raw)
            result.setdefault("name", name)
            result.setdefault("source", entry.source or result.get("source") or entry.source_system)
            result.setdefault("source_system", entry.source_system)
            result.setdefault("rules_version", entry.rules_version)
            return result

        result: Dict[str, Any] = {
            "name": name,
            "hp": {"average": self._parse_hp_average(raw.get("hp"))},
            "ac": self._parse_ac(raw.get("ac")),
            "attack_bonus": self._parse_attack_bonus(raw),
            "damage": self._parse_damage(raw) or "1d6",
            "xp": self._parse_xp(raw),
            "challenge_rating": self._normalize_cr(raw.get("challenge_rating") or raw.get("cr")),
            "source": entry.source,
            "source_system": entry.source_system,
            "rules_version": entry.rules_version,
            "raw": raw,
        }
        return result

    @staticmethod
    def _looks_like_normalized_monster(raw: Dict[str, Any]) -> bool:
        return (
            isinstance(raw.get("hp"), dict)
            and "average" in raw.get("hp", {})
            and "attack_bonus" in raw
            and "damage" in raw
        )

    @property
    def is_loaded(self) -> bool:
        return bool(self._bestiary) or bool(self.compendium_index and self.compendium_index.list_entries())

    @property
    def is_compendium_backed(self) -> bool:
        return self.compendium_index is not None

    # ------------------------------------------------------------------
    # Lightweight monster normalization helpers for compendium raw entries.
    # These intentionally mirror the existing tools/import_5etools_bestiary.py
    # behavior without making BestiaryService depend on that CLI tool.
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_hp_average(hp_value: Any) -> int:
        if isinstance(hp_value, dict):
            average = hp_value.get("average") or hp_value.get("avg")
            if isinstance(average, int):
                return average
            if isinstance(average, str) and average.isdigit():
                return int(average)
            formula = hp_value.get("formula")
            if isinstance(formula, str):
                parsed = _extract_first_int(formula)
                if parsed is not None:
                    return parsed
        if isinstance(hp_value, int):
            return hp_value
        if isinstance(hp_value, str):
            parsed = _extract_first_int(hp_value)
            if parsed is not None:
                return parsed
        return 10

    @staticmethod
    def _parse_ac(ac_value: Any) -> Any:
        if isinstance(ac_value, int):
            return ac_value
        if isinstance(ac_value, list):
            for entry in ac_value:
                if isinstance(entry, dict):
                    value = entry.get("value")
                    if isinstance(value, int):
                        return value
                    if isinstance(value, str) and value.isdigit():
                        return int(value)
                elif isinstance(entry, int):
                    return entry
            return ac_value[0] if ac_value else 10
        if isinstance(ac_value, dict):
            value = ac_value.get("value") or ac_value.get("ac")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        if isinstance(ac_value, str):
            parsed = _extract_first_int(ac_value)
            if parsed is not None:
                return parsed
        return 10

    @staticmethod
    def _parse_attack_bonus(item: Dict[str, Any]) -> int:
        attack_bonus = item.get("attack_bonus") or item.get("to_hit") or item.get("toHit")
        if isinstance(attack_bonus, int):
            return attack_bonus
        if isinstance(attack_bonus, str):
            parsed = _extract_first_int(attack_bonus)
            if parsed is not None:
                return parsed

        actions = item.get("actions") or item.get("action") or []
        if isinstance(actions, dict):
            actions = [actions]
        for action in actions if isinstance(actions, list) else []:
            if not isinstance(action, dict):
                continue
            for field in ["attack_bonus", "attackBonus", "to_hit", "toHit", "bonus"]:
                value = action.get(field)
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    parsed = _extract_first_int(value)
                    if parsed is not None:
                        return parsed
            desc = str(action.get("desc") or action.get("description") or "")
            parsed = _extract_attack_bonus_from_text(desc)
            if parsed is not None:
                return parsed
        return 2

    @staticmethod
    def _parse_damage(item: Dict[str, Any]) -> Optional[str]:
        damage_field = item.get("damage") or item.get("damage_dice")
        if isinstance(damage_field, str) and _is_dice_expression(damage_field):
            return damage_field
        if isinstance(damage_field, dict):
            formula = damage_field.get("formula") or damage_field.get("damage_dice")
            if isinstance(formula, str) and _is_dice_expression(formula):
                return formula

        actions = item.get("actions") or item.get("action") or []
        if isinstance(actions, dict):
            actions = [actions]
        for action in actions if isinstance(actions, list) else []:
            if not isinstance(action, dict):
                continue
            damages = action.get("damage") or action.get("damage_dice")
            if isinstance(damages, str) and _is_dice_expression(damages):
                return damages
            if isinstance(damages, dict):
                dice = damages.get("damage_dice") or damages.get("formula")
                if isinstance(dice, str) and _is_dice_expression(dice):
                    return dice
            desc = str(action.get("desc") or action.get("description") or "")
            dice = _extract_first_dice_expression(desc)
            if dice:
                return dice
        return None

    @staticmethod
    def _parse_xp(item: Dict[str, Any]) -> int:
        xp = item.get("xp")
        if isinstance(xp, int):
            return xp
        if isinstance(xp, str) and xp.isdigit():
            return int(xp)
        cr = BestiaryService._normalize_cr(item.get("challenge_rating") or item.get("cr"))
        return CR_XP_MAP.get(cr or "", 10)

    @staticmethod
    def _normalize_cr(raw: Any) -> Optional[str]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            if raw == 0.125:
                return "1/8"
            if raw == 0.25:
                return "1/4"
            if raw == 0.5:
                return "1/2"
            return str(int(raw)) if float(raw).is_integer() else str(raw)
        return str(raw).strip().lower()


CR_XP_MAP = {
    "0": 10,
    "1/8": 25,
    "1/4": 50,
    "1/2": 100,
    "1": 200,
    "2": 450,
    "3": 700,
    "4": 1100,
    "5": 1800,
    "6": 2300,
    "7": 2900,
    "8": 3900,
    "9": 5000,
    "10": 5900,
    "11": 7200,
    "12": 8400,
    "13": 10000,
    "14": 11500,
    "15": 13000,
    "16": 15000,
    "17": 18000,
    "18": 20000,
    "19": 22000,
    "20": 25000,
    "21": 33000,
    "22": 41000,
    "23": 50000,
    "24": 62000,
    "25": 75000,
    "26": 90000,
    "27": 105000,
    "28": 120000,
    "29": 135000,
    "30": 155000,
}


def _extract_first_int(text: str) -> Optional[int]:
    match = re.search(r"(-?\d+)", str(text or ""))
    if match:
        return int(match.group(1))
    return None


def _is_dice_expression(text: str) -> bool:
    return bool(re.search(r"\d+d\d+(?:[+-]\d+)?", str(text or "")))


def _extract_first_dice_expression(text: str) -> Optional[str]:
    match = re.search(r"\d+d\d+(?:[+-]\d+)?", str(text or ""))
    return match.group(0) if match else None


def _extract_attack_bonus_from_text(text: str) -> Optional[int]:
    match = re.search(r"\+(-?\d+)", str(text or ""))
    if match:
        return int(match.group(1))
    return None
