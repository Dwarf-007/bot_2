from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RuntimeVisibilityIntent:
    kind: str  # LOOK | MOVE | SEARCH_SECRET | MAP | NONE
    direction: Optional[str] = None
    choice: Optional[int] = None
    trait: str = "secret"
    map_mode: str = "local"  # local | full
    raw_text: str = ""


class RuntimeVisibilityIntentParser:
    """Deterministic intent parser for visibility-aware dungeon play."""

    DIRECTION_ALIASES = {
        "north": "north", "n": "north", "észak": "north", "eszak": "north", "északra": "north", "eszakra": "north",
        "south": "south", "s": "south", "dél": "south", "del": "south", "délre": "south", "delre": "south",
        "east": "east", "e": "east", "kelet": "east", "keletre": "east",
        "west": "west", "w": "west", "nyugat": "west", "nyugatra": "west",
        "up": "up", "fel": "up", "felfelé": "up", "felfele": "up",
        "down": "down", "le": "down", "lefelé": "down", "lefele": "down",
        "tovább": "forward", "tovabb": "forward", "előre": "forward", "elore": "forward", "forward": "forward",
        "vissza": "back", "hátra": "back", "hatra": "back", "back": "back",
    }

    LOOK_PATTERNS = (
        r"^\s*(look|exits|kijáratok|kijaratok|ajtók|ajtok)\s*$",
        r"\b(körülnézek|korulnezek|körbenézek|korbenezek|mit látok|mit latok|merre lehet menni)\b",
    )

    FULL_MAP_PATTERNS = (
        r"^\s*(teljes\s+térkép|teljes\s+terkep|szint\s+térkép|szint\s+terkep|full\s+map|level\s+map)\s*$",
        r"\b(teljes.*térkép|teljes.*terkep|egész.*térkép|egesz.*terkep)\b",
    )

    LOCAL_MAP_PATTERNS = (
        r"^\s*(map|térkép|terkep|helyi\s+térkép|helyi\s+terkep|közeli\s+térkép|kozeli\s+terkep|local\s+map|nearby\s+map)\s*$",
        r"^\s*(mutasd a térképet|mutasd a terkepet|rajzold ki a térképet|rajzold ki a terkepet)\s*$",
        r"\b(térképet kérek|terkepet kerek|mutasd.*térkép|mutasd.*terkep)\b",
    )

    SECRET_PATTERNS = (
        r"\b(rejtett ajtót keresek|rejtett ajtot keresek|titkos ajtót keresek|titkos ajtot keresek)\b",
        r"\b(search secret|search secret door|secret door|átvizsgálom a falat|atvizsgalom a falat)\b",
    )

    MOVE_PATTERNS = (
        r"\b(?:megyek|megyünk|megyunk|indulok|indulunk|move|go|menjünk|menjunk)\s+(?P<dir>[a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+)",
        r"^\s*(?P<dir>north|south|east|west|up|down|n|s|e|w|észak|eszak|dél|del|kelet|nyugat|fel|le|tovább|tovabb|előre|elore|vissza|hátra|hatra|forward|back)\s*(?P<choice>\d+)?\s*$",
        r"^\s*(?:megyünk|megyunk|megyek|menjünk|menjunk|go|move)?\s*(?P<choice>\d+)\s*$",
    )

    CHOICE_RE = re.compile(r"(?:--choice\s+|#|\bchoice\s+|\bopció\s+|\bopcio\s+)?(?P<choice>\d+)\b", re.I)

    def parse(self, text: str) -> RuntimeVisibilityIntent:
        raw = str(text or "").strip()
        low = raw.lower()
        if not raw:
            return RuntimeVisibilityIntent("NONE", raw_text=raw)

        if any(re.search(p, low, re.I) for p in self.FULL_MAP_PATTERNS):
            return RuntimeVisibilityIntent("MAP", map_mode="full", raw_text=raw)

        if any(re.search(p, low, re.I) for p in self.LOCAL_MAP_PATTERNS):
            return RuntimeVisibilityIntent("MAP", map_mode="local", raw_text=raw)

        if any(re.search(p, low, re.I) for p in self.LOOK_PATTERNS):
            return RuntimeVisibilityIntent("LOOK", raw_text=raw)

        if any(re.search(p, low, re.I) for p in self.SECRET_PATTERNS):
            return RuntimeVisibilityIntent("SEARCH_SECRET", trait="secret", raw_text=raw)

        for pattern in self.MOVE_PATTERNS:
            m = re.search(pattern, low, re.I)
            if not m:
                continue
            gd = m.groupdict()
            choice = None
            choice_raw = gd.get("choice")
            if choice_raw:
                choice = int(choice_raw)
            else:
                cm = self.CHOICE_RE.search(low)
                if cm:
                    choice = int(cm.group("choice"))
            direction = self._normalise_direction(gd.get("dir")) or "forward"
            return RuntimeVisibilityIntent("MOVE", direction=direction, choice=choice, raw_text=raw)

        return RuntimeVisibilityIntent("NONE", raw_text=raw)

    def _normalise_direction(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return self.DIRECTION_ALIASES.get(str(value).strip().lower())
