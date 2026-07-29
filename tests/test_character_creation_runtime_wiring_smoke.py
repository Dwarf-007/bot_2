from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.character_creation_runtime_wiring_smoke import CharacterCreationRuntimeWiringSmoke


def test_character_creation_runtime_wiring_smoke_green_path():
    result = CharacterCreationRuntimeWiringSmoke().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "runtime_components_composed" in names
    assert "donjon_runtime_turn_output" in names
    assert "sandbox_runtime_dict_payload_turn_output" in names
    assert "spellcaster_runtime_turn_output" in names
    assert "incomplete_request_runtime_turn_output" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["entries"] >= 7


def test_character_creation_runtime_wiring_smoke_machine_readable_output():
    result = CharacterCreationRuntimeWiringSmoke().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 7
    assert "CharacterCreation runtime wiring smoke:" in result.summary_text()


def test_run_character_creation_runtime_wiring_smoke_script_outputs_summary():
    script = Path("scripts/run_character_creation_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CharacterCreation runtime wiring smoke:" in result.stdout
    assert "donjon_runtime_turn_output" in result.stdout
    assert "sandbox_runtime_dict_payload_turn_output" in result.stdout


def test_run_character_creation_runtime_wiring_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_character_creation_runtime_wiring_smoke.py")
    out = tmp_path / "character_creation_runtime_wiring_smoke.json"

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


def test_run_character_creation_runtime_wiring_smoke_script_quiet_mode():
    script = Path("scripts/run_character_creation_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
