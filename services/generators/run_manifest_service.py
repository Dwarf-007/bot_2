from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any, Dict

class RunManifestService:
    def write_manifest(self, output_dir: str|Path, name: str, payload: Dict[str, Any]) -> str:
        root=Path(output_dir); root.mkdir(parents=True, exist_ok=True)
        data={'name': name, 'created_at': time.time(), **(payload or {})}
        path=root/(name if name.endswith('.json') else name+'.json')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)
    def read_manifest(self, path: str|Path) -> Dict[str, Any]:
        return json.loads(Path(path).read_text(encoding='utf-8'))
