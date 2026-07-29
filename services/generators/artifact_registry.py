from __future__ import annotations
import json, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class ArtifactManifest:
    run_id: str
    provider: str
    campaign_id: str
    status: str
    created_at: float
    output_dir: str = ''
    files: Dict[str, str] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    error: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        return asdict(self)

class ArtifactRegistry:
    def __init__(self, registry_file: str | Path = 'campaigns/artifact_registry.jsonl'):
        self.registry_file = Path(registry_file)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
    def append(self, manifest: ArtifactManifest) -> None:
        with self.registry_file.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(manifest.to_dict(), ensure_ascii=False, sort_keys=True) + chr(10))
    def create_manifest(self, provider: str, campaign_id: str, status: str, output_dir: str = '', files: Optional[Dict[str, str]] = None, request: Optional[Dict[str, Any]] = None, diagnostics: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        return ArtifactManifest(
            run_id=f'{provider}_{campaign_id}_{int(time.time()*1000)}',
            provider=provider,
            campaign_id=campaign_id,
            status=status,
            created_at=time.time(),
            output_dir=output_dir,
            files=files or {},
            request=request or {},
            diagnostics=diagnostics or {},
            error=error or {},
            metadata=metadata or {},
        )
    def list(self, campaign_id: str | None = None, limit: int = 100):
        if not self.registry_file.exists():
            return []
        out=[]
        for line in self.registry_file.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            d=json.loads(line)
            if campaign_id and d.get('campaign_id') != campaign_id:
                continue
            out.append(ArtifactManifest(**d))
        return out[-limit:]
