from __future__ import annotations
import json, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict
@dataclass(frozen=True)
class RateLimitDecision:
    allowed:bool; wait_seconds:float=0.0; reason:str=''; state:Dict[str,Any]|None=None
    def to_dict(self): return asdict(self)
class RateLimitGuard:
    def __init__(self, state_file:str|Path='.cache/generator_rate_limits.json'):
        self.state_file=Path(state_file); self.state_file.parent.mkdir(parents=True, exist_ok=True)
    def _load(self):
        if not self.state_file.exists(): return {}
        try: return json.loads(self.state_file.read_text(encoding='utf-8'))
        except Exception: return {}
    def check(self, key:str, min_interval_seconds:float=10.0, now:float|None=None):
        now=time.time() if now is None else float(now); state=self._load(); last=float(state.get(key,{}).get('last_run_at',0)); elapsed=now-last
        if elapsed<min_interval_seconds: return RateLimitDecision(False, min_interval_seconds-elapsed, 'rate_limited', state.get(key,{}))
        return RateLimitDecision(True,0,'allowed',state.get(key,{}))
    def commit(self, key:str, metadata:Dict[str,Any]|None=None, now:float|None=None):
        state=self._load(); state[key]={'last_run_at': time.time() if now is None else float(now), 'metadata': metadata or {}}
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
