from pathlib import Path
from models.runtime_mode import RuntimeMode, RuntimeModeSignals, RuntimeSourceType
from services.runtime_mode_service import RuntimeModeService

def test_dungeon_mode_from_bundle_visibility_signals():
    decision = RuntimeModeService().decide(RuntimeModeSignals(bundle_available=True, map_available=True, visibility_available=True))
    assert decision.mode == RuntimeMode.DUNGEON
    assert decision.dungeon_runtime_enabled is True

def test_campaign_mode_from_rag_signal():
    decision = RuntimeModeService().decide(RuntimeModeSignals(rag_available=True, source_type=RuntimeSourceType.RAG_ONLY))
    assert decision.mode == RuntimeMode.CAMPAIGN
    assert decision.campaign_runtime_enabled is True

def test_sandbox_mode_from_sandbox_signal():
    decision = RuntimeModeService().decide(RuntimeModeSignals(sandbox_enabled=True))
    assert decision.mode == RuntimeMode.SANDBOX
    assert decision.sandbox_runtime_enabled is True

def test_hybrid_mode_from_dungeon_and_rag_signals():
    decision = RuntimeModeService().decide(RuntimeModeSignals(bundle_available=True, map_available=True, visibility_available=True, rag_available=True))
    assert decision.mode == RuntimeMode.HYBRID
    assert decision.dungeon_runtime_enabled is True
    assert decision.campaign_runtime_enabled is True

def test_unknown_mode_without_signals():
    decision = RuntimeModeService().decide(RuntimeModeSignals())
    assert decision.mode == RuntimeMode.UNKNOWN

def test_inspect_bundle_dir_detects_visibility_and_map(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "corridor_visibility_graph.json").write_text("{}", encoding="utf-8")
    (bundle / "level_01_player_map.png").write_bytes(b"name detection only")
    inspected = RuntimeModeService().inspect_bundle_dir(bundle)
    assert inspected["bundle_available"] is True
    assert inspected["visibility_available"] is True
    assert inspected["map_available"] is True

def test_decide_for_bundle_returns_dungeon(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "corridor_visibility_graph.json").write_text("{}", encoding="utf-8")
    decision = RuntimeModeService().decide_for_bundle(campaign_id="c1", channel_id="ch1", bundle_dir=bundle)
    assert decision.mode == RuntimeMode.DUNGEON
