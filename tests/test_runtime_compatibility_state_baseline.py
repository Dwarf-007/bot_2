from services.runtime_compatibility_service import RuntimeCompatibilityService
from services.runtime_visibility_state_service import RuntimeVisibilityStateService


def test_validate_state_baseline():
    result = RuntimeCompatibilityService.validate_state_baseline(RuntimeVisibilityStateService())
    assert result["ok"] is True
    assert result["checks"]["legacy_last_fallback_disabled"] is True
