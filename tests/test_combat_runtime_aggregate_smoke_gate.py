from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.combat_runtime_aggregate_smoke_gate import CombatRuntimeAggregateSmokeGate


def test_combat_runtime_aggregate_smoke_gate_green_path():
    result = CombatRuntimeAggregateSmokeGate().run(channel_id="c5-aggregate")

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "combat_runtime_smoke_service" in names
    assert "combat_runtime_no_legacy_avrae_commands" in names
    assert "canonical_files_present" in names
    assert "no_auto_avrae_dispatch_markers" in names
    assert "no_legacy_avrae_command_event_producers" in names
    assert "turn_output_advisory_contract_present" in names
    assert result.smoke_result["ok"] is True


def test_combat_runtime_aggregate_smoke_gate_machine_readable_output():
    result = CombatRuntimeAggregateSmokeGate().run(channel_id="c5-aggregate-json")
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["smoke_result"]["ok"] is True
    assert "Combat Runtime aggregate smoke gate:" in result.summary_text()


def test_run_combat_runtime_aggregate_smoke_script_outputs_summary():
    script = Path("scripts/run_combat_runtime_aggregate_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--channel-id", "c5-script"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Combat Runtime aggregate smoke gate:" in result.stdout
    assert "no_auto_avrae_dispatch_markers" in result.stdout


def test_run_combat_runtime_aggregate_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_combat_runtime_aggregate_smoke.py")
    out = tmp_path / "aggregate_smoke.json"

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
    assert any(check["name"] == "no_auto_avrae_dispatch_markers" and check["ok"] for check in data["checks"])


def test_run_combat_runtime_aggregate_smoke_script_quiet_mode():
    script = Path("scripts/run_combat_runtime_aggregate_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
