from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass(frozen=True)
class GeneratorHealthItem:
    name: str
    status: str
    message: str = ''
    details: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class GeneratorHealthReport:
    status: str
    checks: List[GeneratorHealthItem] = field(default_factory=list)
    def to_dict(self): return {'status': self.status, 'checks': [c.to_dict() for c in self.checks]}
    def to_text(self):
        icons={'OK':'✅','WARN':'⚠️','FAIL':'❌'}
        lines=[f"**Generator health:** {icons.get(self.status,'ℹ️')} `{self.status}`"]
        for c in self.checks:
            lines.append(f"{icons.get(c.status,'ℹ️')} **{c.name}** — `{c.status}` — {c.message}")
            if c.details:
                lines.append('   `' + ', '.join(f'{k}={v}' for k,v in c.details.items()) + '`')
        return '\n'.join(lines)
