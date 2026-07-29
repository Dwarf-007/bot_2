def test_smoke_script_imports():
    import scripts.run_dungeon_runtime_mvp_smoke as mod
    assert hasattr(mod, "main")
    assert hasattr(mod, "parse_args")
