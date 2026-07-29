def test_runtime_container_declares_runtime_services():
    from app.bootstrap import RuntimeContainer
    fields = set(getattr(RuntimeContainer, "__dataclass_fields__", {}).keys())
    assert "runtime_mode_service" in fields
    assert "runtime_visibility_state_service" in fields
    assert "runtime_visibility_command_handler" in fields
    assert "runtime_visibility_adapter" in fields
