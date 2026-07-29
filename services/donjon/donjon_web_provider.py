"""
SERVICES/GENERATORS/DONJON_WEB_PROVIDER.PY

Sprint 5: Donjon browser automation provider.

This provider uses Playwright if installed. It deliberately imports Playwright
lazily so the rest of the AI DM project can run without browser dependencies.

Workflow:
1. Open Donjon dungeon generator page.
2. Fill supported form fields using configurable selectors.
3. Click Generate/Construct.
4. Try to download JSON/PDF exports if links are present.
5. Always save an HTML snapshot and screenshot for debugging.

Selector stability note:
External sites can change. The provider tries multiple fallback selectors and
records warnings instead of failing for every missing optional field.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin

from services.donjon.donjon_web_config import DonjonWebSelectors, DONJON_FORM_FIELDS
from services.generators.web_automation_models import WebGenerationRequest, WebGenerationResult


class DonjonWebProvider:
    provider_name = "donjon_web"

    def __init__(self, selectors: Optional[DonjonWebSelectors] = None) -> None:
        self.selectors = selectors or DonjonWebSelectors()

    def generate(self, request: WebGenerationRequest) -> WebGenerationResult:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        except Exception as exc:
            raise RuntimeError(
                "Playwright is required for DonjonWebProvider. Install with: pip install playwright && playwright install chromium"
            ) from exc

        output = Path(request.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []
        downloads: dict[str, str] = {}
        json_file: Optional[str] = None
        pdf_file: Optional[str] = None
        campaign_name = request.campaign_name or request.dungeon_name or request.campaign_id

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=request.headless, slow_mo=request.slow_mo_ms)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(request.timeout_ms)
            page.goto(request.url, wait_until="domcontentloaded")

            self._fill_form(page, request, warnings)
            self._click_generate(page, warnings)
            self._wait_after_generate(page, request.timeout_ms, warnings)

            html_file = output / "donjon_result.html"
            html_file.write_text(page.content(), encoding="utf-8")
            screenshot_file = output / "donjon_result.png"
            try:
                page.screenshot(path=str(screenshot_file), full_page=True)
            except Exception as exc:
                warnings.append(f"Could not save screenshot: {exc}")
                screenshot_file = None

            json_file = self._download_first_matching(page, self.selectors.json_links, output, "donjon_export.json", warnings)
            if json_file:
                downloads["json"] = json_file
            else:
                warnings.append("No JSON export link was found. Use saved HTML/screenshot to adjust selectors or export manually.")

            pdf_file = self._download_first_matching(page, self.selectors.pdf_links, output, "donjon_export.pdf", warnings)
            if pdf_file:
                downloads["pdf"] = pdf_file

            current_url = page.url
            context.close()
            browser.close()

        result = WebGenerationResult(
            campaign_id=request.campaign_id,
            campaign_name=campaign_name,
            provider=self.provider_name,
            output_dir=str(output),
            page_url=current_url,
            json_file=json_file,
            pdf_file=pdf_file,
            html_file=str(html_file),
            screenshot_file=str(screenshot_file) if screenshot_file else None,
            downloads=downloads,
            warnings=warnings,
            metadata={"request": request.to_dict(), "selectors": self.selectors.to_dict()},
        )
        (output / "web_generation_result.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _fill_form(self, page: Any, request: WebGenerationRequest, warnings: list[str]) -> None:
        values: dict[str, Any] = {}
        for field_name in DONJON_FORM_FIELDS:
            if field_name == "dungeon_name":
                value = request.dungeon_name or request.campaign_name
            else:
                value = getattr(request, field_name, None)
            if value is not None:
                values[field_name] = value
        values.update(request.custom_fields or {})
        form_fields = dict(self.selectors.form_fields)
        for key, override in (request.selector_overrides or {}).items():
            form_fields[key] = [override]

        for field_name, value in values.items():
            if value is None:
                continue
            selectors = form_fields.get(field_name, [f"[name='{field_name}']", f"#{field_name}"])
            if not self._fill_first(page, selectors, str(value)):
                warnings.append(f"Could not fill optional field '{field_name}'. Tried selectors: {selectors}")

    def _fill_first(self, page: Any, selectors: Iterable[str], value: str) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() <= 0:
                    continue
                tag_name = locator.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "select":
                    try:
                        locator.select_option(label=value)
                    except Exception:
                        locator.select_option(value=value)
                else:
                    locator.fill(value)
                return True
            except Exception:
                continue
        return False

    def _click_generate(self, page: Any, warnings: list[str]) -> None:
        for selector in self.selectors.generate_button:
            try:
                locator = page.locator(selector).first
                if locator.count() <= 0:
                    continue
                locator.click()
                return
            except Exception:
                continue
        raise RuntimeError(f"Could not find/click Donjon generate button. Tried: {self.selectors.generate_button}")

    def _wait_after_generate(self, page: Any, timeout_ms: int, warnings: list[str]) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 60_000))
        except Exception:
            warnings.append("Timed out waiting for networkidle after generation; continuing with current page state.")
        time.sleep(1)

    def _download_first_matching(self, page: Any, selectors: Iterable[str], output_dir: Path, fallback_name: str, warnings: list[str]) -> Optional[str]:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() <= 0:
                    continue
                href = locator.get_attribute("href")
                if href:
                    url = urljoin(page.url, href)
                    return self._download_link(page, locator, output_dir, fallback_name, warnings, url=url)
                return self._download_link(page, locator, output_dir, fallback_name, warnings)
            except Exception as exc:
                warnings.append(f"Download selector failed ({selector}): {exc}")
        return None

    def _download_link(self, page: Any, locator: Any, output_dir: Path, fallback_name: str, warnings: list[str], url: Optional[str] = None) -> Optional[str]:
        try:
            with page.expect_download(timeout=20_000) as download_info:
                locator.click()
            download = download_info.value
            suggested = download.suggested_filename or fallback_name
            target = output_dir / suggested
            download.save_as(str(target))
            return str(target)
        except Exception as click_exc:
            if not url:
                warnings.append(f"Click-download failed and no href URL fallback is available: {click_exc}")
                return None
        try:
            response = page.request.get(url, timeout=30_000)
            if not response.ok:
                warnings.append(f"HTTP download failed for {url}: status={response.status}")
                return None
            target = output_dir / fallback_name
            target.write_bytes(response.body())
            return str(target)
        except Exception as exc:
            warnings.append(f"HTTP fallback download failed for {url}: {exc}")
            return None
