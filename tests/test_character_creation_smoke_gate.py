from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.character_creation_smoke_gate import CharacterCreationSmokeGate


def test_character_creation_smoke_gate_green_path():
    result = CharacterCreationSmokeGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "fixture_entries_loaded" in names
    assert "donjon_scout_advice" in names
    assert "sandbox_frontliner_advice" in names
    assert "spellcaster_review_advice" in names
    assert "missing_choice_reporting" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["entries"] >= 7


def test_character_creation_smoke_gate_machine_readable_output():
    result = CharacterCreationSmokeGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 7
    assert "CharacterCreationAdvisor smoke gate:" in result.summary_text()


def test_run_character_creation_smoke_script_outputs_summary():
    script = Path("scripts/run_character_creation_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CharacterCreationAdvisor smoke gate:" in result.stdout
    assert "donjon_scout_advice" in result.stdout
    assert "missing_choice_reporting" in result.stdout


def test_run_character_creation_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_character_creation_smoke.py")
    out = tmp_path / "character_creation_smoke.json"

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


def test_run_character_creation_smoke_script_quiet_mode():
    script = Path("scripts/run_character_creation_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
