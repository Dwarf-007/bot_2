from __future__ import annotations
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.generators.generator_runtime_health_service import GeneratorRuntimeHealthService
from services.generators.provider_registry import build_default_provider_registry
from services.generators.run_manifest_service import RunManifestService

def main():
    root=Path('_tmp_sprint8')
    if root.exists(): shutil.rmtree(root)
    root.mkdir()
    report=GeneratorRuntimeHealthService(cache_dir=root/'cache', registry_file=root/'registry.jsonl').run_all(include_playwright=False)
    assert report.status in {'OK','WARN','FAIL'}
    assert any(c.name=='cache_dir' for c in report.checks)
    reg=build_default_provider_registry()
    assert reg.get('donjon_json') is not None
    path=RunManifestService().write_manifest(root, 'manifest', {'ok': True})
    assert RunManifestService().read_manifest(path)['ok'] is True
    shutil.rmtree(root)
    print('OK Sprint8 generator health')
if __name__=='__main__': main()
