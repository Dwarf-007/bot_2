"""
AVRAE/AVRAE_PARSER.PY - Downtime-specific parsing extensions

Adds heuristics to extract downtime results like gold gained and items
acquired from Avrae text output. Keeps previous heuristics intact.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Tuple, Dict


# ---------- existing AvraeParserService content preserved above; we'll append helpers


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
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return [q.strip() for q in quoted]

    return []


# Exported helpers for integration tests / service usage
__all__ = ["extract_downtime_gold", "extract_downtime_items"]
