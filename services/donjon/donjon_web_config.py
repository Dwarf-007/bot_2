"""
SERVICES/GENERATORS/DONJON_WEB_CONFIG.PY

Selector configuration for Donjon browser automation.

Important:
Donjon is an external website and can change without notice. Therefore selectors
are configurable and multiple fallback selectors are tried.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Canonical Donjon web form-field catalog. Single source of truth shared by the
# command parser, the provider form filler and the selector configuration.
DONJON_FORM_FIELDS: Tuple[str, ...] = (
    "seed", "dungeon_name", "dungeon_level", "party_level", "n_pc", "infest",
    "size", "layout", "theme", "motif", "peripheral_egress", "room_layout",
    "room_size", "room_polymorph", "doors", "corridor_layout",
    "remove_deadends", "stairs", "image_size", "map_style", "grid",
)


# Canonical allowed values for every Donjon dungeon-generator form field.
# Empty list => free-form text/number (no fixed enumeration).
# Single source of truth for the full option range; surfaced to the LLM so it
# can pick valid values when it generates its own dungeon.
DONJON_FIELD_OPTIONS: Dict[str, List[str]] = {
    "seed": [],  # free-form seed (text/integer)
    "dungeon_name": [],  # free-form name
    "dungeon_level": [str(n) for n in range(1, 21)],  # 1..20
    "party_level": [str(n) for n in range(1, 21)],  # 1..20
    "n_pc": [str(n) for n in range(1, 11)],  # Party Size 1..10
    "infest": ["None", "Few", "Some", "Many", "Lots", "All"],  # Details
    "size": ["Fine", "Diminutive", "Tiny", "Small", "Medium", "Large",
             "Huge", "Gargantuan", "Colossal", "Custom"],
    "layout": ["Standard", "Classic", "Organic", "Room", "Maze",
               "Castle", "Cavern", "Crypt"],
    "theme": [],  # free-form theme
    "motif": ["None", "Abandoned", "Aberrant", "Giant", "Undead", "Vermin",
              "Aquatic", "Desert", "Underdark", "Arcane", "Fire", "Cold",
              "Abyssal", "Infernal"],
    "peripheral_egress": ["No", "Yes", "Many", "Tiling"],
    "room_layout": ["Sparse", "Scattered", "Dense", "Symmetric"],
    "room_size": ["Small", "Medium", "Large", "Huge", "Gargantuan", "Colossal"],
    "room_polymorph": ["No", "Yes", "Many"],
    "doors": ["None", "Basic", "Secure", "Standard", "Deathtrap"],
    "corridor_layout": ["Labyrinth", "Errant", "Straight"],
    "remove_deadends": ["None", "Some", "All"],
    "stairs": ["No", "Yes", "Many"],
    "image_size": ["Small", "Medium", "Large", "Huge"],
    "map_style": ["Standard", "Classic", "Crosshatch", "GraphPaper", "Parchment",
                  "Marble", "Sandstone", "Slate", "Aquatic", "Infernal",
                  "Glacial", "Wooden", "Asylum", "Steampunk", "Gamma"],
    "grid": ["None", "Square", "Hex", "VertHex"],
}


def describe_donjon_options() -> str:
    """Render the full Donjon option catalog as text for prompts / the LLM."""
    lines = ["**Donjon dungeon-generator opciók (teljes választék):**"]
    for field, values in DONJON_FIELD_OPTIONS.items():
        if values:
            lines.append(f"- `--{field.replace('_', '-')}`: {', '.join(values)}")
        else:
            lines.append(f"- `--{field.replace('_', '-')}`: szabad szöveg (nincs rögzített lista)")
    return "\n".join(lines)


@dataclass(frozen=True)
class DonjonWebSelectors:
    generate_button: List[str] = field(default_factory=lambda: [
        "input[type=submit][value*=Construct]",
        "input[type=submit][value*=Generate]",
        "button:has-text('Construct')",
        "button:has-text('Generate')",
        "input[type=submit]",
    ])
    json_links: List[str] = field(default_factory=lambda: [
        "a[href$='.json']",
        "a:has-text('JSON')",
        "a:has-text('json')",
        "a[href*='json']",
    ])
    pdf_links: List[str] = field(default_factory=lambda: [
        "a[href$='.pdf']",
        "a:has-text('PDF')",
        "a:has-text('pdf')",
        "a[href*='pdf']",
    ])
    form_fields: Dict[str, List[str]] = field(default_factory=lambda: {
        "seed": ["input[name='seed']", "#seed"],
        "dungeon_name": ["input[name='dungeon_name']", "input[name='name']", "#dungeon_name", "#name"],
        "dungeon_level": ["select[name='dungeon_level']", "select[name='level']", "input[name='level']"],
        "party_level": ["select[name='party_level']", "select[name='party']", "input[name='party_level']"],
        "size": ["select[name='size']", "select[name='dungeon_size']", "#size"],
        "layout": ["select[name='layout']", "select[name='dungeon_layout']", "#layout"],
        "theme": ["select[name='theme']", "input[name='theme']", "#theme"],
        "peripheral_egress": ["select[name='peripheral_egress']", "#peripheral_egress"],
        "room_layout": ["select[name='room_layout']", "#room_layout"],
        "room_size": ["select[name='room_size']", "#room_size"],
        "doors": ["select[name='doors']", "#doors"],
        "corridor_layout": ["select[name='corridor_layout']", "#corridor_layout"],
        "remove_deadends": ["select[name='remove_deadends']", "#remove_deadends"],
        "stairs": ["select[name='stairs']", "#stairs"],
        "map_style": ["select[name='map_style']", "#map_style"],
        "grid": ["select[name='grid']", "#grid"],
        "motif": ["select[name='motif']", "#motif"],
        "room_polymorph": ["select[name='room_polymorph']", "#room_polymorph"],
        "infest": ["select[name='infest']", "#infest"],
        "n_pc": ["select[name='n_pc']", "#n_pc"],
        "image_size": ["select[name='image_size']", "#image_size"],
    })

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_file(cls, path: str | Path) -> "DonjonWebSelectors":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            generate_button=list(data.get("generate_button", cls().generate_button)),
            json_links=list(data.get("json_links", cls().json_links)),
            pdf_links=list(data.get("pdf_links", cls().pdf_links)),
            form_fields=dict(data.get("form_fields", cls().form_fields)),
        )
