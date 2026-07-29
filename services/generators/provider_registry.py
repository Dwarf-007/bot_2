from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    name: str
    kind: str
    enabled: bool = True
    description: str = ''
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, ProviderDescriptor] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
    def register(self, descriptor: ProviderDescriptor, factory: Optional[Callable[[], Any]]=None):
        self._providers[descriptor.provider_id]=descriptor
        if factory: self._factories[descriptor.provider_id]=factory
    def get(self, provider_id: str) -> Optional[ProviderDescriptor]: return self._providers.get(provider_id)
    def create(self, provider_id: str):
        if provider_id not in self._factories: raise KeyError(f'No factory registered for provider: {provider_id}')
        return self._factories[provider_id]()
    def list(self, enabled_only: bool=False):
        values=list(self._providers.values())
        if enabled_only: values=[v for v in values if v.enabled]
        return sorted(values, key=lambda d:d.provider_id)
    def to_dict(self): return {'providers':[p.to_dict() for p in self.list()]}

def build_default_provider_registry() -> ProviderRegistry:
    reg=ProviderRegistry()
    reg.register(ProviderDescriptor('donjon_json','Donjon JSON Importer','local_import',True,'Import existing Donjon JSON export',['import','bundle']))
    reg.register(ProviderDescriptor('donjon_web','Donjon Web Provider','web_automation',True,'Generate via Donjon website using Playwright',['web','download','json','pdf']))
    reg.register(ProviderDescriptor('donjon_web_v2','Donjon Web Provider V2','web_automation',True,'Web provider with cache and diagnostics',['web','cache','diagnostics']))
    reg.register(ProviderDescriptor('donjon_web_hardened','Hardened Donjon Web Runner','web_automation',True,'Retry/rate-limit/quarantine wrapper',['retry','rate_limit','registry','quarantine']))
    return reg
