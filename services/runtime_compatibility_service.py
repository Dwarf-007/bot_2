from __future__ import annotations


class RuntimeCompatibilityService:
    """Lightweight integration validator introduced in Sprint 10.8 and extended in Sprint 11.3."""

    @staticmethod
    def validate_container(container) -> dict:
        checks = {
            "runtime_mode_service": hasattr(container, "runtime_mode_service"),
            "runtime_mode_router": hasattr(container, "runtime_mode_router"),
            "runtime_visibility_state_service": hasattr(container, "runtime_visibility_state_service"),
            "runtime_visibility_command_handler": hasattr(container, "runtime_visibility_command_handler"),
            "runtime_visibility_adapter": hasattr(container, "runtime_visibility_adapter"),
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
        }

    @staticmethod
    def validate_state_baseline(state_service) -> dict:
        checks = {
            "legacy_last_fallback_disabled": getattr(state_service, "enable_legacy_last_fallback", None) is False,
            "has_reset_state": hasattr(state_service, "reset_state"),
            "has_describe_state_files": hasattr(state_service, "describe_state_files"),
            "has_cleanup_debug_mirror": hasattr(state_service, "cleanup_debug_mirror"),
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
        }
