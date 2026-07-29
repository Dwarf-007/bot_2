from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.compendium_integration_smoke_gate import CompendiumIntegrationSmokeGate


def test_compendium_integration_smoke_gate_green_path():
    result = CompendiumIntegrationSmokeGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "fiveetools_data_source_loaded_entries" in names
    assert "compendium_index_built" in names
    assert "bestiary_service_compendium_lookup" in names
    assert "rules_reference_condition_lookup" in names
    assert "spell_reference_lookup" in names
    assert "character_option_class_and_feature_lookup" in names
    assert "level_up_advisor_checklist" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["entries"] >= 8


def test_compendium_integration_smoke_gate_machine_readable_output():
    result = CompendiumIntegrationSmokeGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 8
    assert "Compendium integration smoke gate:" in result.summary_text()


def test_run_compendium_integration_smoke_script_outputs_summary():
    script = Path("scripts/run_compendium_integration_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Compendium integration smoke gate:" in result.stdout
    assert "rules_reference_condition_lookup" in result.stdout
    assert "level_up_advisor_checklist" in result.stdout


def test_run_compendium_integration_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_compendium_integration_smoke.py")
    out = tmp_path / "compendium_smoke.json"

    result = subprocess.run(
        [sys.executable, str(script), "--json-out", str(out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert any(check["name"] == "no_avrae_or_discord_runtime_coupling" and check["ok"] for check in data["checks"])


def test_run_compendium_integration_smoke_script_quiet_mode():
    script = Path("scripts/run_compendium_integration_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
