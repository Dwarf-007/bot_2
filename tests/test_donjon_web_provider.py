"""
Sprint 5 non-network tests.
Run from project root:
    python tests/test_donjon_web_provider.py

This test intentionally does NOT open Donjon and does NOT require Playwright.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.donjon.donjon_web_command_parser import DonjonWebCommandParser
from services.donjon.donjon_web_config import DonjonWebSelectors
from services.generators.web_automation_models import WebGenerationRequest, WebGenerationResult


def main() -> None:
    selectors = DonjonWebSelectors()
    assert selectors.generate_button
    assert "theme" in selectors.form_fields

    req, options = DonjonWebCommandParser().parse('donjon_web sakka --name "Sakka" --theme Undead --size Large --import --clear-rag --max-rooms 5')
    assert isinstance(req, WebGenerationRequest)
    assert req.campaign_id == "sakka"
    assert req.campaign_name == "Sakka"
    assert req.theme == "Undead"
    assert req.size == "Large"
    assert options["import_to_runtime"] is True
    assert options["clear_rag"] is True
    assert options["max_rooms"] == 5

    result = WebGenerationResult(
        campaign_id="sakka",
        campaign_name="Sakka",
        provider="donjon_web",
        output_dir="campaigns/web/sakka",
        page_url="https://example.invalid",
        warnings=["test warning"],
    )
    assert "Web generation finished" in result.to_text()
    print("OK DonjonWebProvider models/parser")


if __name__ == "__main__":
    main()
