from __future__ import annotations
import json, shutil, time
from pathlib import Path
from typing import Any, Dict
class FailedRunQuarantine:
    def __init__(self, root_dir:str|Path='campaigns/_failed_generator_runs'):
        self.root_dir=Path(root_dir); self.root_dir.mkdir(parents=True, exist_ok=True)
    def quarantine(self, provider:str, campaign_id:str, source_dir:str|Path, error:BaseException|str, request:Dict[str,Any]|None=None)->str:
        target=self.root_dir/f'{provider}_{campaign_id}_{time.strftime("%Y%m%d_%H%M%S")}' ; target.mkdir(parents=True, exist_ok=True)
        src=Path(source_dir)
        if src.exists() and src.is_dir():
            for item in src.iterdir():
                if item.is_file(): shutil.copy2(item, target/item.name)
        payload={'provider':provider,'campaign_id':campaign_id,'error_type':type(error).__name__ if isinstance(error,BaseException) else 'Error','error_message':str(error),'request':request or {},'created_at':time.time()}
        (target/'failure.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(target)
