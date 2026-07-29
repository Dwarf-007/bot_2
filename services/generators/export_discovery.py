from __future__ import annotations
import json, re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List
from urllib.parse import urljoin

@dataclass(frozen=True)
class ExportCandidate:
    kind: str
    url: str
    text: str = ''
    score: int = 0
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ExportDiscoveryReport:
    source_file: str
    base_url: str = ''
    candidates: List[ExportCandidate] = field(default_factory=list)
    def best_json(self): return self._best('json')
    def best_pdf(self): return self._best('pdf')
    def _best(self, kind):
        xs=[c for c in self.candidates if c.kind == kind]
        return sorted(xs, key=lambda c: c.score, reverse=True)[0] if xs else None
    def to_dict(self):
        return {'source_file': self.source_file, 'base_url': self.base_url, 'candidates': [c.to_dict() for c in self.candidates]}

class ExportDiscovery:
    HREF_RE = re.compile(r'<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', re.I | re.S)
    def discover_file(self, html_file: str|Path, base_url: str='', output_json: str|Path|None=None):
        p=Path(html_file)
        rep=self.discover_html(p.read_text(encoding='utf-8', errors='replace'), str(p), base_url)
        if output_json:
            Path(output_json).write_text(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        return rep
    def discover_html(self, html: str, source_file='<memory>', base_url=''):
        candidates=[]
        for href, txt in self.HREF_RE.findall(html or ''):
            text=re.sub(r'<[^>]+>', ' ', txt)
            text=re.sub(r'\s+', ' ', text).strip()
            low=(href + ' ' + text).lower()
            url=urljoin(base_url, href)
            if 'json' in low or href.lower().endswith('.json'):
                candidates.append(ExportCandidate('json', url, text, self._score(low, 'json')))
            if 'pdf' in low or href.lower().endswith('.pdf'):
                candidates.append(ExportCandidate('pdf', url, text, self._score(low, 'pdf')))
        candidates.sort(key=lambda c: (c.kind, -c.score, c.url))
        return ExportDiscoveryReport(source_file, base_url, candidates)
    @staticmethod
    def _score(low, kind):
        return (50 if '.' + kind in low else 0) + (20 if kind in low else 0) + (10 if 'download' in low or 'export' in low else 0)
