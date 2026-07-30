"""
AVRAE/AVRAE_PARSER.PY
Parser utilities for Avrae Discord messages and embeds.

This is intentionally heuristic: Avrae message formats can vary. The parser
extracts useful signals without becoming a second combat rules engine.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Tuple, Dict


class AvraeParserService:
    @staticmethod
    def extract_full_text(message_or_embeds) -> str:
        if hasattr(message_or_embeds, "content"):
            content = message_or_embeds.content or ""
            embeds = getattr(message_or_embeds, "embeds", []) or []
            return (content + "\n" + AvraeParserService.extract_full_text(embeds)).strip()

        embeds = message_or_embeds or []
        if not isinstance(embeds, list):
            embeds = [embeds]

        fragments: List[str] = []
        for embed in embeds:
            fragments.append(str(getattr(embed, "title", "") or ""))
            fragments.append(str(getattr(embed, "description", "") or ""))
            author = getattr(embed, "author", None)
            fragments.append(str(getattr(author, "name", "") or ""))
            for field in getattr(embed, "fields", []) or []:
                fragments.append(str(getattr(field, "name", "") or ""))
                fragments.append(str(getattr(field, "value", "") or ""))
        return "\n".join(part for part in fragments if part).strip()

    @staticmethod
    def is_avrae_message(message) -> bool:
        author = getattr(message, "author", None)
        name = str(getattr(author, "name", "") or "").lower()
        display_name = str(getattr(author, "display_name", "") or "").lower()
        return "avrae" in name or "avrae" in display_name

    @staticmethod
    def is_combat_trigger(text: str) -> bool:
        lower = (text or "").lower()
        return any(keyword in lower for keyword in ["initiative", "combat", "kezdeményezés", "init"])

    @staticmethod
    def is_hp_update(text: str) -> bool:
        lower = (text or "").lower()
        return "hp:" in lower or "hit points" in lower or "❤️" in text

    @staticmethod
    def is_death_event(text: str) -> bool:
        lower = (text or "").lower()
        return any(keyword in lower for keyword in ["dead", "dying", "defeated", "killed", "0 hp"])

    @staticmethod
    def extract_defeated_names(text: str) -> List[str]:
        """
        Heuristic extraction of defeated monster names from Avrae-like text.

        Supported patterns include examples like:
        - "Goblin is dead"
        - "Goblin defeated"
        - "Killed: Goblin"
        - "Goblin drops to 0 HP"
        """

        if not text:
            return []

        patterns = [
            r"(?im)^\s*(?P<name>[A-Za-z][A-Za-z0-9_ '\-]{1,60})\s+(?:is\s+)?(?:dead|defeated|killed)\b",
            r"(?im)\b(?:dead|defeated|killed)\s*[:\-]\s*(?P<name>[A-Za-z][A-Za-z0-9_ '\-]{1,60})",
            r"(?im)^\s*(?P<name>[A-Za-z][A-Za-z0-9_ '\-]{1,60})\s+(?:drops|falls)\s+to\s+0\s*hp\b",
        ]

        names: List[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                name = AvraeParserService._clean_name(match.group("name"))
                if name and name.lower() not in {n.lower() for n in names}:
                    names.append(name)
        return names

    @staticmethod
    def extract_current_turn_name(text: str) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"It is now\s+(.+?)'s turn", text or "", re.I)
        if match:
            return AvraeParserService._clean_name(match.group(1))
        return None

    @staticmethod
    def extract_roll_results(text: str) -> List[Dict[str, Any]]:
        if not text:
            return []

        results: List[Dict[str, Any]] = []
        patterns = [
            r"(?im)^(?P<actor>.+?)\s+rolls?\s+(?P<formula>[\d dD+\-()]+?)\s*=\s*(?P<total>\d+)\b",
            r"(?im)^(?P<actor>.+?)\s+rolled\s+(?P<formula>[\d dD+\-()]+?)\s*=\s*(?P<total>\d+)\b",
            r"(?im)^(?P<actor>.+?)\s+total\s*[:=]\s*(?P<total>\d+)\b",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                actor = AvraeParserService._clean_name(match.group("actor"))
                formula = match.groupdict().get("formula") or ""
                total = int(match.group("total"))
                if actor or formula:
                    results.append({"actor": actor, "formula": str(formula).strip(), "total": total})

        if not results and re.search(r"\brolled\b|\brolls?\b|\btotal\b", text or "", re.I):
            total = AvraeParserService.extract_total_roll(text)
            if total is not None:
                results.append({"actor": "", "formula": "", "total": total})

        return results

    @staticmethod
    def extract_total_roll(text: str) -> Optional[int]:
        match = re.search(r"=\s*(\d+)", text or "")
        if match:
            return int(match.group(1))
        numbers = re.findall(r"\b\d+\b", text or "")
        if numbers:
            return int(numbers[-1])
        return None

    @staticmethod
    def evaluate_roll_status(total_roll: int, dc: int) -> Tuple[str, str]:
        target_dc = dc if dc > 0 else 12
        success = total_roll >= target_dc
        return ("SUCCESS" if success else "FAILURE"), f"DC {target_dc}"

    @staticmethod
    def _clean_name(value: str) -> str:
        text = re.sub(r'[*_`>\"]', '', str(value or '')).strip()
        text = re.sub(r"\s+", " ", text)
        return text.strip(" .:-")


# Downtime-specific helpers
def extract_downtime_gold(text: str) -> Optional[int]:
    """
    Heuristic to extract a gold/coin gain from downtime messages.
    Matches patterns like:
      - "You earned 25 gp"
      - "Gained 10 gold"
      - "You receive 2d6 gp"

    Returns an integer when a simple numeric value is found (dice expressions not rolled).
    """
    if not text:
        return None
    # Common patterns
    patterns = [
        r"(?:earned|gained|receive|received)\s+(?P<amt>\d+)\s*(?:gp|gold)",
        r"(?P<amt>\d+)\s*(?:gp|gold)\s*(?:earned|gained|received)?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                return int(m.group("amt"))
            except (TypeError, ValueError):
                continue
    return None


def extract_downtime_items(text: str) -> List[str]:
    """
    Heuristic to extract named items from downtime result text.
    Matches patterns like:
      - "You acquired: Potion of Healing"
      - "Gained items: Sword, Shield"
    Returns a list of item names (best-effort).
    """
    if not text:
        return []
    # look for 'gained', 'acquired', 'received', 'items' markers followed by colon or list
    m = re.search(r"(?:gained|acquired|received|items?)\s*[:\-]\s*(?P<list>.+)$", text, re.I | re.M)
    items: List[str] = []
    if m:
        raw = m.group("list")
        # split by commas and 'and'
        parts = re.split(r",| and ", raw)
        for p in parts:
            name = p.strip().strip('.\n\r')
            if name:
                items.append(name)
        return items

    # fallback: look for quoted names
    quoted = re.findall(r'"([^\"]+)"', text)
    if quoted:
        return [q.strip() for q in quoted]

    return []


__all__ = ["AvraeParserService", "extract_downtime_gold", "extract_downtime_items"]
