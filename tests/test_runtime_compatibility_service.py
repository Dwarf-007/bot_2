from services.runtime_compatibility_service import RuntimeCompatibilityService

class Dummy:
    runtime_mode_service=object()
    runtime_visibility_state_service=object()
    runtime_visibility_command_handler=object()
    runtime_visibility_adapter=object()


def test_validate_container():
    result = RuntimeCompatibilityService.validate_container(Dummy())
    assert result['ok'] is True
