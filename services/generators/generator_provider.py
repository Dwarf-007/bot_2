"""
SERVICES/GENERATORS/GENERATOR_PROVIDER.PY

Generic provider interface for procedural dungeon sources.

Examples of future implementations:
- DonjonJsonImporter       local JSON import
- DonjonWebProvider        Playwright/Selenium automation
- WatabouProvider          city/dungeon import
- AzgaarProvider           world import
- LocalJsonDungeonProvider project-native JSON import
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from models.generated_dungeon import GeneratedDungeon


@dataclass(frozen=True)
class GenerationRequest:
    campaign_id: str
    title: str = "Generated Dungeon"
    source_path: Optional[Path] = None
    provider: str = "manual"
    theme: Optional[str] = None
    size: Optional[str] = None
    seed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GeneratorProvider(Protocol):
    provider_name: str

    def generate(self, request: GenerationRequest) -> GeneratedDungeon:
        """Return a source-agnostic GeneratedDungeon."""
        raise NotImplementedError
