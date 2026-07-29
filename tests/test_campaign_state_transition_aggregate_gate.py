from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.compendium.campaign_state_transition_aggregate_gate import CampaignStateTransitionAggregateGate


def test_campaign_state_transition_aggregate_gate_green_path():
    result = CampaignStateTransitionAggregateGate().run()

    assert result.ok is True, result.summary_text()
    names = [check.name for check in result.checks]
    assert "g1_05_runtime_wiring_smoke" in names
    assert "proposal_generation_contract" in names
    assert "approval_policy_contract" in names
    assert "application_turn_output_contract" in names
    assert "never_auto_contract" in names
    assert "no_avrae_or_discord_runtime_coupling" in names
    assert "no_campaign_state_mutation" in names
    assert result.stats["g1_05_ok"] is True
    assert result.stats["proposal_count"] >= 1


def test_campaign_state_transition_aggregate_gate_machine_readable_output():
    result = CampaignStateTransitionAggregateGate().run()
    data = result.to_dict()

    assert data["ok"] is True
    assert data["checks"]
    assert data["stats"]["proposal_count"] >= 1
    assert "CampaignStateTransition G1 aggregate gate:" in result.summary_text()


def test_run_campaign_state_transition_aggregate_gate_script_outputs_summary():
    script = Path("scripts/run_campaign_state_transition_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "CampaignStateTransition G1 aggregate gate:" in result.stdout
    assert "application_turn_output_contract" in result.stdout


def test_run_campaign_state_transition_aggregate_gate_script_writes_json(tmp_path):
    script = Path("scripts/run_campaign_state_transition_aggregate_gate.py")
    out = tmp_path / "campaign_state_transition_g1_aggregate.json"

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
    assert any(check["name"] == "no_campaign_state_mutation" and check["ok"] for check in data["checks"])


def test_run_campaign_state_transition_aggregate_gate_script_quiet_mode():
    script = Path("scripts/run_campaign_state_transition_aggregate_gate.py")

    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "OK"
