def test_runtime_container_declares_runtime_mode_router():
    from app.bootstrap import RuntimeContainer
    fields = set(getattr(RuntimeContainer, "__dataclass_fields__", {}).keys())
    assert "runtime_mode_service" in fields
    assert "runtime_mode_router" in fields
    assert "runtime_visibility_adapter" in fields
