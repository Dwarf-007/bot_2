from __future__ import annotations
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.generators.download_cache import DownloadCache
from services.generators.export_discovery import ExportDiscovery
from services.generators.selector_diagnostics import SelectorDiagnostics

HTML = """
<html><body><form>
<input type="text" name="seed" value="abc">
<select name="size"><option>Large</option></select>
<select name="theme"><option>Undead</option></select>
<input type="submit" value="Construct Dungeon">
</form><a href="/tmp/example.json">JSON</a><a href="/tmp/example.pdf">PDF</a></body></html>
"""

def main():
    root=Path('_tmp_sprint6');
    if root.exists(): shutil.rmtree(root)
    root.mkdir(); html=root/'snapshot.html'; html.write_text(HTML, encoding='utf-8')
    diag=SelectorDiagnostics().analyze_file(html); assert any(i.group=='json_links' and i.status=='LIKELY_PRESENT' for i in diag.items)
    disc=ExportDiscovery().discover_file(html, 'https://donjon.example/base/'); assert disc.best_json() and disc.best_pdf()
    art=root/'artifact.json'; art.write_text('{"ok": true}', encoding='utf-8')
    cache=DownloadCache(root/'cache'); rec=cache.store('donjon_web_v2', {'campaign_id':'x','theme':'Undead'}, {'json':str(art)})
    assert cache.find('donjon_web_v2', {'campaign_id':'x','theme':'Undead'}) is not None
    out=cache.materialize(rec, root/'out'); assert Path(out['json']).exists()
    shutil.rmtree(root); print('OK Sprint6 diagnostics/cache')
if __name__=='__main__': main()
