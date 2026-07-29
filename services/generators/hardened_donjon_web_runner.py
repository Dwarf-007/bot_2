from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
from services.generators.artifact_registry import ArtifactRegistry
from services.generators.failed_run_quarantine import FailedRunQuarantine
from services.generators.rate_limit_guard import RateLimitGuard
from services.generators.retry_policy import RetryExecutor, RetryPolicy
from services.generators.selector_autosuggest import SelectorAutoSuggest
try:
    from services.donjon.donjon_web_provider_v2 import DonjonWebProviderV2
except Exception:
    DonjonWebProviderV2=None
class HardenedDonjonWebRunner:
    def __init__(self, provider:Optional[Any]=None, retry_policy:Optional[RetryPolicy]=None, rate_limit_guard:Optional[RateLimitGuard]=None, registry:Optional[ArtifactRegistry]=None, quarantine:Optional[FailedRunQuarantine]=None, autosuggest:Optional[SelectorAutoSuggest]=None, min_interval_seconds:float=10.0):
        self.provider=provider or (DonjonWebProviderV2() if DonjonWebProviderV2 else None); self.retry_policy=retry_policy or RetryPolicy(); self.rate_limit_guard=rate_limit_guard or RateLimitGuard(); self.registry=registry or ArtifactRegistry(); self.quarantine=quarantine or FailedRunQuarantine(); self.autosuggest=autosuggest or SelectorAutoSuggest(); self.min_interval_seconds=min_interval_seconds
    def run(self, request:Any, use_cache:bool=True, refresh_cache:bool=False):
        if not self.provider: raise RuntimeError('DonjonWebProviderV2 is unavailable. Apply Sprint 5+6 first.')
        key=f"donjon_web:{getattr(request,'campaign_id','unknown')}"; decision=self.rate_limit_guard.check(key,self.min_interval_seconds)
        if not decision.allowed: raise RuntimeError(f'Rate limited. Wait {decision.wait_seconds:.1f}s before retrying.')
        output_dir=Path(getattr(request,'output_dir','campaigns/web/unknown')); output_dir.mkdir(parents=True, exist_ok=True); executor=RetryExecutor(self.retry_policy)
        try:
            result=executor.run(lambda: self.provider.generate(request, use_cache=use_cache, refresh_cache=refresh_cache)); self.rate_limit_guard.commit(key, {'status':'OK'})
            manifest=self.registry.create_manifest('donjon_web_hardened', getattr(request,'campaign_id','unknown'), 'OK', str(output_dir), self._files_from_result(result), request.to_dict() if hasattr(request,'to_dict') else {}, {'retry_attempts':executor.attempts_as_dicts()}, metadata={'warnings':getattr(result,'warnings',[])})
            self.registry.append(manifest); return result
        except Exception as exc:
            suggestion_file=None; html_file=output_dir/'donjon_result.html'
            if html_file.exists(): suggestion_file=output_dir/'selector_suggestions.json'; self.autosuggest.suggest_file(html_file, suggestion_file)
            qdir=self.quarantine.quarantine('donjon_web_hardened', getattr(request,'campaign_id','unknown'), output_dir, exc, request.to_dict() if hasattr(request,'to_dict') else {})
            manifest=self.registry.create_manifest('donjon_web_hardened', getattr(request,'campaign_id','unknown'), 'FAIL', str(output_dir), {'selector_suggestions':str(suggestion_file)} if suggestion_file else {}, request.to_dict() if hasattr(request,'to_dict') else {}, {'retry_attempts':executor.attempts_as_dicts(),'quarantine_dir':qdir}, {'type':type(exc).__name__,'message':str(exc)})
            self.registry.append(manifest); raise
    def _files_from_result(self,result):
        files={}
        for label,attr in [('json','json_file'),('pdf','pdf_file'),('html','html_file'),('screenshot','screenshot_file')]:
            val=getattr(result,attr,None)
            if val: files[label]=str(val)
        return files
