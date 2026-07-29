from services.dungeon_runtime_mvp_commands import DungeonRuntimeMvpCommandCatalog


def test_catalog_recognizes_mvp_commands():
    catalog = DungeonRuntimeMvpCommandCatalog()
    assert catalog.is_mvp_command("look") is True
    assert catalog.is_mvp_command("megyek északra") is True
    assert catalog.is_mvp_command("map") is True
    assert catalog.is_mvp_command("teljes térkép") is True
    assert catalog.is_mvp_command("titkos ajtót keresek") is True


def test_catalog_rejects_free_chat():
    catalog = DungeonRuntimeMvpCommandCatalog()
    assert catalog.is_mvp_command("beszélgetek a kereskedővel") is False
    assert catalog.is_mvp_command("mi a történet háttere?") is False


def test_help_text_contains_core_commands():
    text = DungeonRuntimeMvpCommandCatalog().help_text()
    assert "LOOK" in text
    assert "MOVE" in text
    assert "MAP" in text
    assert "SEARCH_SECRET" in text
