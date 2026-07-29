from __future__ import annotations
import hashlib, json, shutil, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class CachedArtifactRecord:
    cache_key: str
    provider: str
    created_at: float
    request_hash: str
    request: Dict[str, Any]
    files: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

class DownloadCache:
    def __init__(self, root_dir: str | Path = '.cache/generated_dungeons'):
        self.root_dir = Path(root_dir); self.root_dir.mkdir(parents=True, exist_ok=True)
    def make_key(self, provider: str, request: Dict[str, Any]) -> str:
        normalized=json.dumps(request or {}, ensure_ascii=False, sort_keys=True, default=str)
        return f"{provider}_{hashlib.sha256((provider+'\n'+normalized).encode()).hexdigest()[:24]}"
    def get_record_path(self, cache_key: str) -> Path: return self.root_dir/cache_key/'cache_record.json'
    def get_record(self, cache_key: str) -> Optional[CachedArtifactRecord]:
        p=self.get_record_path(cache_key)
        if not p.exists(): return None
        d=json.loads(p.read_text(encoding='utf-8'))
        return CachedArtifactRecord(d['cache_key'], d['provider'], float(d.get('created_at',0)), d.get('request_hash',''), d.get('request',{}), d.get('files',{}), d.get('metadata',{}))
    def find(self, provider: str, request: Dict[str, Any]) -> Optional[CachedArtifactRecord]:
        return self.get_record(self.make_key(provider, request))
    def store(self, provider: str, request: Dict[str, Any], files: Dict[str,str], metadata: Optional[Dict[str,Any]]=None, copy_files: bool=True) -> CachedArtifactRecord:
        key=self.make_key(provider, request); d=self.root_dir/key; d.mkdir(parents=True, exist_ok=True); stored={}
        for label, name in (files or {}).items():
            if not name: continue
            src=Path(name)
            if not src.exists(): continue
            if copy_files:
                dst=d/src.name
                if src.resolve()!=dst.resolve(): shutil.copy2(src,dst)
                stored[label]=str(dst)
            else: stored[label]=str(src)
        rh=hashlib.sha256(json.dumps(request or {}, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
        rec=CachedArtifactRecord(key, provider, time.time(), rh, request or {}, stored, metadata or {})
        self.get_record_path(key).write_text(json.dumps(rec.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        return rec
    def materialize(self, record: CachedArtifactRecord, output_dir: str|Path) -> Dict[str,str]:
        out=Path(output_dir); out.mkdir(parents=True, exist_ok=True); result={}
        for label,name in (record.files or {}).items():
            src=Path(name)
            if src.exists():
                dst=out/src.name; shutil.copy2(src,dst); result[label]=str(dst)
        return result
    def clear(self) -> int:
        c=0
        for item in list(self.root_dir.iterdir()) if self.root_dir.exists() else []:
            if item.is_dir(): shutil.rmtree(item); c+=1
        self.root_dir.mkdir(parents=True, exist_ok=True); return c
