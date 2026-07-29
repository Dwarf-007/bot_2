from __future__ import annotations
import importlib, shutil
from pathlib import Path
from typing import Any, Optional
from services.generators.generator_health_models import GeneratorHealthItem, GeneratorHealthReport

class GeneratorRuntimeHealthService:
    MODULES = [
        'services.donjon.donjon_json_importer',
        'services.generators.campaign_bundle_builder',
        'services.generators.campaign_enricher',
        'services.generators.generation_orchestrator',
        'services.donjon.donjon_web_provider',
        'services.donjon.donjon_web_provider_v2',
        'services.generators.hardened_donjon_web_runner',
    ]
    def __init__(self, cache_dir: str|Path='.cache/generated_dungeons', registry_file: str|Path='campaigns/artifact_registry.jsonl'):
        self.cache_dir=Path(cache_dir); self.registry_file=Path(registry_file)
    def run_all(self, include_playwright: bool=True) -> GeneratorHealthReport:
        checks=[]
        for mod in self.MODULES:
            try:
                importlib.import_module(mod); checks.append(GeneratorHealthItem('import:'+mod,'OK','import sikeres'))
            except Exception as exc:
                # Donjon web modules are optional until Sprint5+ installed.
                status='WARN' if 'donjon_web' in mod or 'hardened' in mod else 'FAIL'
                checks.append(GeneratorHealthItem('import:'+mod,status,repr(exc)))
        checks.append(self._dir_check('cache_dir', self.cache_dir))
        checks.append(self._registry_check())
        if include_playwright:
            checks.append(self._playwright_check())
        status='FAIL' if any(c.status=='FAIL' for c in checks) else ('WARN' if any(c.status=='WARN' for c in checks) else 'OK')
        return GeneratorHealthReport(status, checks)
    def _dir_check(self, name, path: Path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe=path/'.write_probe'; probe.write_text('ok', encoding='utf-8'); probe.unlink()
            return GeneratorHealthItem(name,'OK','írható',{'path':str(path)})
        except Exception as exc:
            return GeneratorHealthItem(name,'FAIL','nem írható',{'path':str(path),'error':repr(exc)})
    def _registry_check(self):
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            exists=self.registry_file.exists()
            return GeneratorHealthItem('artifact_registry','OK','registry elérhető',{'path':str(self.registry_file),'exists':exists})
        except Exception as exc:
            return GeneratorHealthItem('artifact_registry','FAIL','registry hiba',{'error':repr(exc)})
    def _playwright_check(self):
        try:
            import playwright  # noqa
            chromium = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
            return GeneratorHealthItem('playwright','OK' if chromium else 'WARN','playwright import OK' + ('' if chromium else ', chromium binary nem látható PATH-ban'), {'chromium': chromium or ''})
        except Exception as exc:
            return GeneratorHealthItem('playwright','WARN','Playwright nincs telepítve; csak web automation érintett',{'error':repr(exc)})
