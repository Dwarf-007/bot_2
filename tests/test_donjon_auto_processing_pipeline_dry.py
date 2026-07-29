from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.donjon.donjon_auto_processing_pipeline import DonjonAutoProcessingPipeline


def main():
    root = Path('_tmp_auto_pipeline_test')
    shutil.rmtree(root, ignore_errors=True)
    (root / 'downloads').mkdir(parents=True)
    (root / 'bundle').mkdir(parents=True)
    (root / 'downloads' / 'donjon_megadungeon_manifest.json').write_text(json.dumps({'levels': []}), encoding='utf-8')
    (root / 'downloads' / 'L01.tsv').write_text('F\tF\nF\tF\n', encoding='utf-8')
    pipeline = DonjonAutoProcessingPipeline(project_root='.')
    manifest = pipeline._resolve_manifest(root / 'downloads', root / 'bundle', None)
    assert manifest and manifest.name == 'donjon_megadungeon_manifest.json'
    copy_result = pipeline._copy_tsv_assets(root / 'downloads', root / 'bundle')
    assert copy_result.ok
    assert (root / 'bundle' / 'L01.tsv').exists()
    shutil.rmtree(root)
    print('OK donjon auto processing pipeline dry')

if __name__ == '__main__':
    main()
