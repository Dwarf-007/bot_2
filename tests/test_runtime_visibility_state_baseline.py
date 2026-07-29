from pathlib import Path
from types import SimpleNamespace

from services.runtime_visibility_state_service import RuntimeVisibilityStateService


def bundle(tmp_path: Path):
    d = tmp_path / "bundle"
    d.mkdir()
    return SimpleNamespace(bundle_dir=d, campaign_id="c1")


def test_default_baseline_disables_legacy_last_fallback():
    svc = RuntimeVisibilityStateService()
    assert svc.enable_legacy_last_fallback is False


def test_authoritative_state_ignores_legacy_last_by_default(tmp_path: Path):
    b = bundle(tmp_path)
    legacy = b.bundle_dir / "visibility_runtime_state_last.json"
    legacy.write_text('{"campaign_id":"legacy","current":{"node_id":"old","node_type":"room","level":1,"room_id":"old"}}', encoding="utf-8")
    svc = RuntimeVisibilityStateService(enable_legacy_last_fallback=False, write_legacy_last=False)
    state = svc.load_or_init_state(b, "ch1", "p1")
    assert state.campaign_id == "c1"
    assert state.current.room_id != "old"
    assert svc.state_file(b, "ch1").exists()


def test_reset_state_overwrites_authoritative_state(tmp_path: Path):
    b = bundle(tmp_path)
    svc = RuntimeVisibilityStateService(write_legacy_last=False)
    first = svc.load_or_init_state(b, "ch1", "p1")
    first.visited_rooms.append("extra")
    svc.save_state(b, "ch1", first)
    reset = svc.reset_state(b, channel_id="ch1", player_id="p1")
    assert "extra" not in reset.visited_rooms
    assert svc.state_file(b, "ch1").exists()


def test_describe_state_files_reports_debug_mirror(tmp_path: Path):
    b = bundle(tmp_path)
    svc = RuntimeVisibilityStateService(write_legacy_last=True)
    svc.load_or_init_state(b, "ch1", "p1")
    desc = svc.describe_state_files(b, "ch1")
    assert desc["authoritative_exists"] is True
    assert "visibility_runtime_state_ch1.json" in desc["authoritative_state_file"]
