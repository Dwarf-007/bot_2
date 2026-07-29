from __future__ import annotations
from services.generators.generator_runtime_health_service import GeneratorRuntimeHealthService
from services.generators.provider_registry import build_default_provider_registry

class GeneratorAdminStatusService:
    def __init__(self, health_service=None, provider_registry=None):
        self.health_service=health_service or GeneratorRuntimeHealthService()
        self.provider_registry=provider_registry or build_default_provider_registry()
    def health_text(self): return self.health_service.run_all().to_text()
    def providers_text(self):
        lines=['**Generator providers:**']
        for p in self.provider_registry.list():
            lines.append(f"- `{p.provider_id}` — {p.name} — `{p.kind}` — {'enabled' if p.enabled else 'disabled'}")
            if p.capabilities: lines.append('  capabilities: `' + ', '.join(p.capabilities) + '`')
        return '\n'.join(lines)
