
"""
MODELS/RUNTIME_HEALTH.PY
DTOs for runtime health checks and diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class HealthCheckItem:
    name: str
    status: str  # OK | WARN | FAIL
    message: str = ""
    details: Dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeHealthReport:
    status: str  # OK | WARN | FAIL
    checks: List[HealthCheckItem] = field(default_factory=list)

    def to_text(self) -> str:
        icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(self.status, "ℹ️")
        lines = [f"**Runtime health:** {icon} `{self.status}`"]
        for item in self.checks:
            item_icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(item.status, "ℹ️")
            lines.append(f"{item_icon} **{item.name}** — `{item.status}` — {item.message}")
            if item.details:
                details = ", ".join(f"{key}={value}" for key, value in item.details.items())
                lines.append(f"   `{details}`")
        return "\n".join(lines)
