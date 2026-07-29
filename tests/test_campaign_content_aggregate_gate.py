from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.campaign_content_aggregate_gate import CampaignContentAggregateGate


def test_campaign_content_aggregate_gate_green_path():
    result = CampaignContentAggregateGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "f3_05_runtime_wiring_smoke" in names
    assert "application_turn_output_contract" in names
    assert "player_safe_dm_only_separation" in names
    assert "approval_checkpoint_contract" in names
    assert "missing_scene_contract" in names
    assert "canonical_f3_files_present" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert result.stats["f3_05_ok"] is True
    assert result.stats["entries"] >= 1


def test_campaign_content_aggregate_gate_machine_readable_output():
    result = CampaignContentAggregateGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["entries"] >= 1
    assert "CampaignContent F3 aggregate gate:" in result.summary_text()


def test_run_campaign_content_aggregate_gate_script_outputs_summary():
    script = Path("scripts/run_campaign_content_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CampaignContent F3 aggregate gate:" in result.stdout
    assert "application_turn_output_contract" in result.stdout


def test_run_campaign_content_aggregate_gate_script_writes_json(tmp_path):
    script = Path("scripts/run_campaign_content_aggregate_gate.py")
    out = tmp_path / "campaign_content_f3_aggregate.json"

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


def test_run_campaign_content_aggregate_gate_script_quiet_mode():
    script = Path("scripts/run_campaign_content_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
