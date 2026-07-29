from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.campaign_state_transition_runtime_wiring_smoke import CampaignStateTransitionRuntimeWiringSmoke


def test_campaign_state_transition_runtime_wiring_smoke_green_path():
    result = CampaignStateTransitionRuntimeWiringSmoke().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "runtime_components_composed" in names
    assert "campaign_goblin_ambush_transition_output" in names
    assert "donjon_trap_transition_output" in names
    assert "sandbox_npc_transition_output" in names
    assert "missing_scene_transition_output" in names
    assert "never_auto_transition_output" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["entries"] >= 1


def test_campaign_state_transition_runtime_wiring_smoke_machine_readable_output():
    result = CampaignStateTransitionRuntimeWiringSmoke().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 1
    assert "CampaignStateTransition runtime wiring smoke:" in result.summary_text()


def test_run_campaign_state_transition_runtime_wiring_smoke_script_outputs_summary():
    script = Path("scripts/run_campaign_state_transition_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CampaignStateTransition runtime wiring smoke:" in result.stdout
    assert "campaign_goblin_ambush_transition_output" in result.stdout
    assert "never_auto_transition_output" in result.stdout


def test_run_campaign_state_transition_runtime_wiring_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_campaign_state_transition_runtime_wiring_smoke.py")
    out = tmp_path / "campaign_state_transition_runtime_wiring_smoke.json"

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


def test_run_campaign_state_transition_runtime_wiring_smoke_script_quiet_mode():
    script = Path("scripts/run_campaign_state_transition_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
