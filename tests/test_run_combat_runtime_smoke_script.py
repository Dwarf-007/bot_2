from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_combat_runtime_smoke_script_outputs_summary():
    script = Path("scripts/run_combat_runtime_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--channel-id", "test-combat-smoke"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Combat Runtime smoke:" in result.stdout
    assert "start_combat_suggested_commands" in result.stdout
    assert "no_avrae_dispatcher_called" in result.stdout


def test_run_combat_runtime_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_combat_runtime_smoke.py")
    json_out = tmp_path / "combat_runtime_smoke.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--channel-id",
            "test-combat-smoke-json",
            "--json-out",
            str(json_out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert json_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["steps"]
    assert data["suggested_commands"]
    assert data["no_legacy_avrae_commands"] is True
    assert any(step["name"] == "no_avrae_dispatcher_called" and step["ok"] for step in data["steps"])


def test_run_combat_runtime_smoke_script_quiet_mode():
    script = Path("scripts/run_combat_runtime_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
