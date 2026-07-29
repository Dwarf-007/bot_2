from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class VisionProfile:
    """Runtime vision/light profile expressed in Donjon grid cells.

    This is intentionally cell-based for now. Later it can be replaced by a true
    LOS/ray-casting implementation without changing the map service API.

    Semantics:
    - bright_radius_cells: cells always included around visible/current cells.
    - dim_radius_cells: optional wider cells included as dim/revealed map cells.
    - respect_corners/respect_walls: reserved flags for a later strict LOS pass.
    - reveal_dim_as_seen: if true, dim cells are added to FoW revealed cells.
    """

    name: str = "torch"
    bright_radius_cells: int = 3
    dim_radius_cells: int = 6
    darkvision_radius_cells: int = 0
    respect_corners: bool = True
    respect_walls: bool = True
    reveal_dim_as_seen: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisionProfiles:
    """Preset registry for runtime visibility map rendering."""

    PRESETS: Dict[str, VisionProfile] = {
        "none": VisionProfile("none", bright_radius_cells=0, dim_radius_cells=0, darkvision_radius_cells=0),
        "darkness": VisionProfile("darkness", bright_radius_cells=0, dim_radius_cells=1, darkvision_radius_cells=0),
        "dim_light": VisionProfile("dim_light", bright_radius_cells=1, dim_radius_cells=3, darkvision_radius_cells=0),
        "torch": VisionProfile("torch", bright_radius_cells=3, dim_radius_cells=6, darkvision_radius_cells=0),
        "lantern": VisionProfile("lantern", bright_radius_cells=4, dim_radius_cells=8, darkvision_radius_cells=0),
        "bullseye_lantern": VisionProfile("bullseye_lantern", bright_radius_cells=6, dim_radius_cells=12, darkvision_radius_cells=0),
        "darkvision_60": VisionProfile("darkvision_60", bright_radius_cells=0, dim_radius_cells=6, darkvision_radius_cells=6),
        "darkvision_120": VisionProfile("darkvision_120", bright_radius_cells=0, dim_radius_cells=12, darkvision_radius_cells=12),
        "daylight": VisionProfile("daylight", bright_radius_cells=8, dim_radius_cells=14, darkvision_radius_cells=0),
    }

    @classmethod
    def get(cls, name: Optional[str]) -> VisionProfile:
        key = str(name or "torch").strip().lower()
        return cls.PRESETS.get(key, cls.PRESETS["torch"])

    @classmethod
    def build(
        cls,
        name: Optional[str] = None,
        *,
        bright_radius_cells: Optional[int] = None,
        dim_radius_cells: Optional[int] = None,
        darkvision_radius_cells: Optional[int] = None,
        respect_corners: Optional[bool] = None,
        respect_walls: Optional[bool] = None,
        reveal_dim_as_seen: Optional[bool] = None,
    ) -> VisionProfile:
        base = cls.get(name)
        return VisionProfile(
            name=str(name or base.name),
            bright_radius_cells=max(0, int(bright_radius_cells if bright_radius_cells is not None else base.bright_radius_cells)),
            dim_radius_cells=max(0, int(dim_radius_cells if dim_radius_cells is not None else base.dim_radius_cells)),
            darkvision_radius_cells=max(0, int(darkvision_radius_cells if darkvision_radius_cells is not None else base.darkvision_radius_cells)),
            respect_corners=base.respect_corners if respect_corners is None else bool(respect_corners),
            respect_walls=base.respect_walls if respect_walls is None else bool(respect_walls),
            reveal_dim_as_seen=base.reveal_dim_as_seen if reveal_dim_as_seen is None else bool(reveal_dim_as_seen),
        )
