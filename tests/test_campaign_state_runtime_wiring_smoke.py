from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.campaign.campaign_state_runtime_wiring_smoke import CampaignStateRuntimeWiringSmoke


def test_campaign_state_runtime_wiring_smoke_green_path():
    result = CampaignStateRuntimeWiringSmoke().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "initial_state_saved" in names
    assert "approved_proposals_applied" in names
    assert "state_contains_location_clue_and_quest_candidate" in names
    assert "query_service_reads_updated_context" in names
    assert "snapshot_roundtrip" in names
    assert "never_auto_is_blocked" in names
    assert "room_alias_bridge" in names
    assert "no_runtime_coupling" in names
    assert result.stats["applied_count"] == 4


def test_campaign_state_runtime_wiring_smoke_machine_readable_output():
    result = CampaignStateRuntimeWiringSmoke().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["known_locations"] >= 1
    assert "CampaignState G2 runtime wiring smoke:" in result.summary_text()


def test_run_campaign_state_runtime_wiring_smoke_script_outputs_summary():
    script = Path("scripts/run_campaign_state_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CampaignState G2 runtime wiring smoke:" in result.stdout
    assert "approved_proposals_applied" in result.stdout


def test_run_campaign_state_runtime_wiring_smoke_script_writes_json(tmp_path):
    script = Path("scripts/run_campaign_state_runtime_wiring_smoke.py")
    out = tmp_path / "campaign_state_runtime_wiring_smoke.json"

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


def test_run_campaign_state_runtime_wiring_smoke_script_quiet_mode():
    script = Path("scripts/run_campaign_state_runtime_wiring_smoke.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
