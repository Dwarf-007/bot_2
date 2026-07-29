from pathlib import Path
from types import SimpleNamespace

from services.dungeon_runtime_state_admin_service import DungeonRuntimeStateAdminService
from services.runtime_visibility_state_service import RuntimeVisibilityStateService


class Resolver:
    def __init__(self, bundle):
        self.bundle = bundle
    def resolve(self, campaign_id):
        return self.bundle


def bundle(tmp_path: Path):
    d = tmp_path / "bundle"
    d.mkdir()
    return SimpleNamespace(bundle_dir=d, campaign_id="c1", visibility_available=True)


def test_admin_status_reports_state_files(tmp_path: Path):
    b = bundle(tmp_path)
    svc = DungeonRuntimeStateAdminService(state_service=RuntimeVisibilityStateService())
    svc.resolver = Resolver(b)
    result = svc.status(campaign_id="c1", channel_id="ch1")
    assert result["ok"] is True
    assert result["visibility_available"] is True
    assert "authoritative_state_file" in result


def test_admin_reset_creates_state(tmp_path: Path):
    b = bundle(tmp_path)
    svc = DungeonRuntimeStateAdminService(state_service=RuntimeVisibilityStateService(write_legacy_last=False))
    svc.resolver = Resolver(b)
    result = svc.reset(campaign_id="c1", channel_id="ch1", player_id="p1")
    assert result["ok"] is True
    assert result["state"] is not None
    assert (b.bundle_dir / "visibility_runtime_state_ch1.json").exists()
