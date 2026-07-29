from __future__ import annotations
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.generators.artifact_registry import ArtifactRegistry
from services.generators.failed_run_quarantine import FailedRunQuarantine
from services.generators.rate_limit_guard import RateLimitGuard
from services.generators.retry_policy import RetryExecutor, RetryPolicy
from services.generators.selector_autosuggest import SelectorAutoSuggest
HTML = "<html><body><form><input type='submit' value='Construct Dungeon'><select name='theme'></select></form><a href='x.json'>JSON</a></body></html>"
def main():
    root=Path('_tmp_sprint7')
    if root.exists(): shutil.rmtree(root)
    root.mkdir(); attempts={'n':0}
    def op():
        attempts['n']+=1
        if attempts['n']<2: raise RuntimeError('transient')
        return 'ok'
    ex=RetryExecutor(RetryPolicy(max_attempts=3, initial_delay_seconds=0, jitter_seconds=0), sleep_func=lambda s: None)
    assert ex.run(op)=='ok'
    guard=RateLimitGuard(root/'rate.json'); assert guard.check('k',10,now=100).allowed; guard.commit('k',now=100); assert not guard.check('k',10,now=105).allowed
    reg=ArtifactRegistry(root/'registry.jsonl'); man=reg.create_manifest('p','c','OK',files={'a':'b'}); reg.append(man); assert len(reg.list('c'))==1
    html=root/'snap.html'; html.write_text(HTML, encoding='utf-8'); suggestions=SelectorAutoSuggest().suggest_file(html, root/'suggest.json'); assert suggestions['generate_button']
    q=FailedRunQuarantine(root/'failed').quarantine('p','c',root,RuntimeError('boom'),{'x':1}); assert Path(q,'failure.json').exists()
    shutil.rmtree(root); print('OK Sprint7 hardening')
if __name__=='__main__': main()
