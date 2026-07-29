from __future__ import annotations
import json, re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    from services.donjon.donjon_web_config import DonjonWebSelectors
except Exception:
    class DonjonWebSelectors:
        def __init__(self):
            self.generate_button=['input[type=submit][value*=Construct]','input[type=submit]']
            self.json_links=["a[href$='.json']", "a:has-text('JSON')", "a[href*='json']"]
            self.pdf_links=["a[href$='.pdf']", "a:has-text('PDF')", "a[href*='pdf']"]
            self.form_fields={'seed':["input[name='seed']",'#seed'], 'size':["select[name='size']",'#size'], 'theme':["select[name='theme']",'#theme'], 'layout':["select[name='layout']",'#layout']}

@dataclass(frozen=True)
class SelectorDiagnosticItem:
    group: str
    selector: str
    status: str
    evidence: str=''
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class SelectorDiagnosticReport:
    source_file: str
    status: str
    items: List[SelectorDiagnosticItem]=field(default_factory=list)
    recommendations: List[str]=field(default_factory=list)
    metadata: Dict[str,Any]=field(default_factory=dict)
    def to_dict(self):
        return {'source_file':self.source_file,'status':self.status,'items':[i.to_dict() for i in self.items],'recommendations':self.recommendations,'metadata':self.metadata}
    def to_text(self):
        lines=[f"Selector diagnostics: `{self.status}`", f"Source: `{self.source_file}`"]
        lines += [f"- {i.group}: `{i.selector}` -> `{i.status}` {i.evidence}" for i in self.items]
        if self.recommendations:
            lines.append('Recommendations:')
            lines += ['- '+r for r in self.recommendations]
        return '\n'.join(lines)

class SelectorDiagnostics:
    def __init__(self, selectors: Optional[DonjonWebSelectors]=None):
        self.selectors=selectors or DonjonWebSelectors()
    def analyze_file(self, html_file: str|Path, output_json: str|Path|None=None):
        p=Path(html_file)
        rep=self.analyze_html(p.read_text(encoding='utf-8', errors='replace'), str(p))
        if output_json:
            Path(output_json).write_text(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        return rep
    def analyze_html(self, html: str, source_file: str='<memory>'):
        items=[]
        for s in self.selectors.generate_button: items.append(self._check('generate_button',s,html))
        for s in self.selectors.json_links: items.append(self._check('json_links',s,html))
        for s in self.selectors.pdf_links: items.append(self._check('pdf_links',s,html))
        for f, sels in self.selectors.form_fields.items():
            for s in sels[:3]: items.append(self._check('field:'+f,s,html))
        ok={i.group for i in items if i.status=='LIKELY_PRESENT'}
        rec=[]
        if 'generate_button' not in ok: rec.append('Generate button selector was not detected.')
        if 'json_links' not in ok: rec.append('JSON export link was not detected.')
        missing=[g for g in ['field:size','field:theme','field:layout'] if g not in ok]
        if missing: rec.append('Some expected form fields were not detected: '+', '.join(missing))
        return SelectorDiagnosticReport(source_file, 'OK' if not rec else 'WARN', items, rec, {'html_size':len(html or '')})
    def _check(self, group, selector, html):
        st, ev=self._match(selector, html or '')
        return SelectorDiagnosticItem(group, selector, st, ev)
    def _match(self, selector, html):
        low=html.lower(); s=selector.strip(); sl=s.lower()
        m=re.search(r"has-text\(['\"]([^'\"]+)['\"]\)", s)
        if m:
            val=m.group(1).lower()
            return ('LIKELY_PRESENT', 'text~='+val) if val in low else ('MISSING','')
        m=re.search(r"\[name=['\"]?([^'\"]+)['\"]?\]", s)
        if m and re.search(r"name\s*=\s*['\"]"+re.escape(m.group(1).lower())+r"['\"]", low):
            return 'LIKELY_PRESENT','name='+m.group(1)
        m=re.search(r"#([A-Za-z0-9_\-]+)", s)
        if m and ('id="'+m.group(1).lower()+'"') in low:
            return 'LIKELY_PRESENT','id='+m.group(1)
        if '.json' in sl and '.json' in low: return 'LIKELY_PRESENT','json href'
        if '.pdf' in sl and '.pdf' in low: return 'LIKELY_PRESENT','pdf href'
        if 'value*=construct' in sl and 'construct' in low: return 'LIKELY_PRESENT','construct text'
        if 'submit' in sl and 'type="submit"' in low: return 'LIKELY_PRESENT','submit input'
        return 'MISSING',''
