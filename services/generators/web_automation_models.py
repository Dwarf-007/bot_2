"""
SERVICES/GENERATORS/WEB_AUTOMATION_MODELS.PY

Sprint 5 model layer for browser-backed dungeon generation providers.

The first provider is DonjonWebProvider. The models are generic enough to be
reused later by Watabou/Azgaar automation adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WebGenerationRequest:
    campaign_id: str
    campaign_name: Optional[str] = None
    output_dir: str = "campaigns/generated_web"
    url: str = "https://donjon.bin.sh/5e/dungeon/"
    headless: bool = True
    timeout_ms: int = 120_000
    slow_mo_ms: int = 0
    seed: Optional[str] = None
    dungeon_name: Optional[str] = None
    dungeon_level: Optional[str] = None
    party_level: Optional[str] = None
    size: Optional[str] = None
    layout: Optional[str] = None
    theme: Optional[str] = None
    peripheral_egress: Optional[str] = None
    room_layout: Optional[str] = None
    room_size: Optional[str] = None
    doors: Optional[str] = None
    corridor_layout: Optional[str] = None
    remove_deadends: Optional[str] = None
    stairs: Optional[str] = None
    map_style: Optional[str] = None
    grid: Optional[str] = None
    motif: Optional[str] = None
    room_polymorph: Optional[str] = None
    infest: Optional[str] = None
    n_pc: Optional[str] = None
    image_size: Optional[str] = None
    custom_fields: Dict[str, str] = field(default_factory=dict)
    selector_overrides: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WebGenerationResult:
    campaign_id: str
    campaign_name: str
    provider: str
    output_dir: str
    page_url: str
    json_file: Optional[str] = None
    pdf_file: Optional[str] = None
    html_file: Optional[str] = None
    screenshot_file: Optional[str] = None
    downloads: Dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def json_path(self) -> Optional[Path]:
        return Path(self.json_file) if self.json_file else None

    def to_text(self) -> str:
        lines = [
            "**Web generation finished**",
            f"Provider: `{self.provider}`",
            f"Campaign: `{self.campaign_id}` — {self.campaign_name}",
            f"Output: `{self.output_dir}`",
        ]
        if self.json_file:
            lines.append(f"JSON: `{self.json_file}`")
        if self.pdf_file:
            lines.append(f"PDF: `{self.pdf_file}`")
        if self.html_file:
            lines.append(f"HTML snapshot: `{self.html_file}`")
        if self.screenshot_file:
            lines.append(f"Screenshot: `{self.screenshot_file}`")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {w}" for w in self.warnings)
        return "\n".join(lines)
