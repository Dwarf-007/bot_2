from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.character_creation_aggregate_gate import CharacterCreationAggregateGate


def test_character_creation_aggregate_gate_green_path():
    result = CharacterCreationAggregateGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "f2_02_character_creation_smoke_gate" in names
    assert "f2_04_runtime_wiring_smoke" in names
    assert "application_turn_output_contract" in names
    assert "canonical_f2_files_present" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["f2_02_ok"] is True
    assert result.stats["f2_04_ok"] is True
    assert result.stats["entries"] >= 7


def test_character_creation_aggregate_gate_machine_readable_output():
    result = CharacterCreationAggregateGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 7
    assert "CharacterCreation F2 aggregate gate:" in result.summary_text()


def test_run_character_creation_aggregate_gate_script_outputs_summary():
    script = Path("scripts/run_character_creation_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CharacterCreation F2 aggregate gate:" in result.stdout
    assert "application_turn_output_contract" in result.stdout


def test_run_character_creation_aggregate_gate_script_writes_json(tmp_path):
    script = Path("scripts/run_character_creation_aggregate_gate.py")
    out = tmp_path / "character_creation_f2_aggregate.json"

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


def test_run_character_creation_aggregate_gate_script_quiet_mode():
    script = Path("scripts/run_character_creation_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
