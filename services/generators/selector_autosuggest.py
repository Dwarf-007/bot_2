from __future__ import annotations
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict

class _SuggestionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.generate_button=[]
        self.json_links=[]
        self.pdf_links=[]
        self.form_fields={}
        self._last_href=None
    def handle_starttag(self, tag, attrs):
        attr=dict(attrs)
        tag=tag.lower()
        if tag in {"input", "select", "textarea"} and attr.get("name"):
            name=attr.get("name")
            self.form_fields.setdefault(name, []).append(f"{tag}[name='{name}']")
        if tag == "input":
            typ=(attr.get("type") or "").lower()
            val=(attr.get("value") or "")
            if typ == "submit" or "construct" in val.lower() or "generate" in val.lower():
                self.generate_button.append("input[type=submit]")
                if val:
                    self.generate_button.append("input[type=submit][value*='" + val.split()[0] + "']")
        if tag == "a":
            href=(attr.get("href") or "")
            if "json" in href.lower(): self.json_links.append("a[href*='json']")
            if "pdf" in href.lower(): self.pdf_links.append("a[href*='pdf']")
            self._last_href=href
    def handle_data(self, data):
        txt=(data or "").lower()
        href=(self._last_href or "").lower()
        if "json" in txt or "json" in href: self.json_links.append("a[href*='json']")
        if "pdf" in txt or "pdf" in href: self.pdf_links.append("a[href*='pdf']")

class SelectorAutoSuggest:
    def suggest_file(self, html_file: str | Path, output_json: str | Path | None = None) -> Dict[str, Any]:
        p = Path(html_file)
        result = self.suggest_html(p.read_text(encoding="utf-8", errors="replace"), str(p))
        if output_json:
            Path(output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    def suggest_html(self, html: str, source_file: str = "<memory>") -> Dict[str, Any]:
        parser=_SuggestionParser(); parser.feed(html or "")
        return {
            "source_file": source_file,
            "generate_button": sorted(set(parser.generate_button)),
            "json_links": sorted(set(parser.json_links)),
            "pdf_links": sorted(set(parser.pdf_links)),
            "form_fields": {k: sorted(set(v)) for k, v in sorted(parser.form_fields.items())},
        }
