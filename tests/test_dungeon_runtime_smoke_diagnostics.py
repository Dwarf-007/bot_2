import json
from pathlib import Path

from services.dungeon_runtime_smoke_diagnostics import DungeonRuntimeSmokeDiagnostics, SmokeStepStatus


def sample_false_green():
    return {
        "ok": True,
        "campaign_id": "tenebrous",
        "channel_id": "smoke-channel",
        "player_id": "smoke-player",
        "bundle_available": True,
        "visibility_available": True,
        "campaign_forced": True,
        "channel_bound": True,
        "smoke_result": {
            "ok": True,
            "steps": [
                {"name": "look", "text": "look", "ok": True, "public_narrative": "Egy keleti folyosószakaszon álltok.", "expected_substring": None},
                {"name": "map", "text": "map", "ok": True, "public_narrative": "A visibility runtime hibát jelzett: unterminated string literal (detected at line 267) (runtime_visibility_map_service.py, line 267)", "expected_substring": None},
                {"name": "move", "text": "megyek északra", "ok": True, "public_narrative": "Több továbbvezető folyosószakasz látszik. Válassz egy sorszámot.", "expected_substring": None},
                {"name": "back", "text": "vissza", "ok": True, "public_narrative": "Nem egyértelmű, merre van vissza.", "expected_substring": None},
                {"name": "search_secret", "text": "titkos ajtót keresek", "ok": True, "public_narrative": "A visibility runtime hibát jelzett: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'SecretDiscoveryStateStore'", "expected_substring": None},
            ],
        },
    }


def test_detects_false_green_runtime_errors():
    diagnosis = DungeonRuntimeSmokeDiagnostics().diagnose(sample_false_green())
    assert diagnosis.original_ok is True
    assert diagnosis.false_green is True
    assert diagnosis.ok is False
    assert diagnosis.false_green_steps == 2
    statuses = {step.name: step.status for step in diagnosis.steps}
    assert statuses["map"] == SmokeStepStatus.FALSE_GREEN_RUNTIME_ERROR
    assert statuses["search_secret"] == SmokeStepStatus.FALSE_GREEN_RUNTIME_ERROR
    assert statuses["move"] == SmokeStepStatus.OK_AMBIGUOUS_CHOICE
    assert statuses["back"] == SmokeStepStatus.OK_NO_BACK_HISTORY


def test_detects_llm_fallback():
    data = sample_false_green()
    data["smoke_result"]["steps"] = [
        {"name": "look", "text": "look", "ok": True, "public_narrative": "A narrációs modell jelenleg nem válaszol megbízhatóan. Kérlek ismételd meg az akciódat rövidebben.", "expected_substring": None}
    ]
    diagnosis = DungeonRuntimeSmokeDiagnostics().diagnose(data)
    assert diagnosis.false_green is True
    assert diagnosis.steps[0].status == SmokeStepStatus.FALSE_GREEN_LLM_FALLBACK


def test_diagnose_file(tmp_path: Path):
    p = tmp_path / "smoke.json"
    p.write_text(json.dumps(sample_false_green(), ensure_ascii=False), encoding="utf-8")
    diagnosis = DungeonRuntimeSmokeDiagnostics().diagnose_file(p)
    assert diagnosis.campaign_id == "tenebrous"
    assert diagnosis.blocking_failures == 2


def test_summary_text_contains_recommendations():
    diagnosis = DungeonRuntimeSmokeDiagnostics().diagnose(sample_false_green())
    text = diagnosis.summary_text()
    assert "false_green=True" in text
    assert "runtime_visibility_map_service.py" in text
    assert "SecretDoorDiscoveryEngine" in text
