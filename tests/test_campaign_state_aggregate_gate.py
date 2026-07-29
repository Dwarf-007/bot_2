from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.campaign.campaign_state_aggregate_gate import CampaignStateAggregateGate


def test_campaign_state_aggregate_gate_green_path():
    result = CampaignStateAggregateGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "g2_05_runtime_wiring_smoke" in names
    assert "model_contract" in names
    assert "store_contract" in names
    assert "application_contract" in names
    assert "query_contract" in names
    assert "no_runtime_coupling" in names
    assert result.stats["g2_05_ok"] is True


def test_campaign_state_aggregate_gate_machine_readable_output():
    result = CampaignStateAggregateGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert "CampaignState G2 aggregate gate:" in result.summary_text()


def test_run_campaign_state_aggregate_gate_script_outputs_summary():
    script = Path("scripts/run_campaign_state_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CampaignState G2 aggregate gate:" in result.stdout
    assert "application_contract" in result.stdout


def test_run_campaign_state_aggregate_gate_script_writes_json(tmp_path):
    script = Path("scripts/run_campaign_state_aggregate_gate.py")
    out = tmp_path / "campaign_state_g2_aggregate.json"

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


def test_run_campaign_state_aggregate_gate_script_quiet_mode():
    script = Path("scripts/run_campaign_state_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
