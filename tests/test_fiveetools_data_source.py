import json

from services.compendium.compendium_models import CompendiumEntryType
from services.compendium.fiveetools_data_source import FiveEToolsDataSource


def test_data_source_loads_known_collections_from_raw_root(tmp_path):
    raw_root = tmp_path / "data" / "compendium" / "fiveetools" / "raw"
    monster_dir = raw_root / "monsters"
    spell_dir = raw_root / "spells"
    monster_dir.mkdir(parents=True)
    spell_dir.mkdir(parents=True)

    (monster_dir / "bestiary-mm.json").write_text(
        json.dumps({
            "monster": [
                {"name": "Goblin", "source": "MM", "page": 166, "cr": "1/4"}
            ]
        }),
        encoding="utf-8",
    )
    (spell_dir / "spells-phb.json").write_text(
        json.dumps({
            "spell": [
                {"name": "Fireball", "source": "PHB", "page": 241, "level": 3, "school": "V"}
            ]
        }),
        encoding="utf-8",
    )

    source = FiveEToolsDataSource(raw_root=raw_root)
    entries = source.load_entries()

    assert len(entries) == 2
    by_name = {entry.name: entry for entry in entries}
    assert by_name["Goblin"].entry_type == CompendiumEntryType.MONSTER
    assert by_name["Goblin"].entry_id == "monster:goblin:mm"
    assert by_name["Goblin"].source == "MM"
    assert by_name["Goblin"].page == 166
    assert "cr:1/4" in by_name["Goblin"].tags

    assert by_name["Fireball"].entry_type == CompendiumEntryType.SPELL
    assert by_name["Fireball"].entry_id == "spell:fireball:phb"
    assert "level:3" in by_name["Fireball"].tags
    assert "school:V" in by_name["Fireball"].tags


def test_data_source_can_filter_by_entry_type(tmp_path):
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    (raw_root / "mixed.json").write_text(
        json.dumps({
            "monster": [{"name": "Goblin", "source": "MM"}],
            "spell": [{"name": "Fireball", "source": "PHB"}],
        }),
        encoding="utf-8",
    )

    source = FiveEToolsDataSource(raw_root=raw_root)
    spells = source.load_entries(entry_types=[CompendiumEntryType.SPELL])

    assert [entry.name for entry in spells] == ["Fireball"]


def test_data_source_supports_list_files_when_collection_can_be_guessed_from_path(tmp_path):
    raw_root = tmp_path / "raw"
    monster_dir = raw_root / "monsters"
    monster_dir.mkdir(parents=True)
    (monster_dir / "custom.json").write_text(
        json.dumps([
            {"name": "Skeleton", "source": "MM", "page": "272"}
        ]),
        encoding="utf-8",
    )

    source = FiveEToolsDataSource(raw_root=raw_root)
    entries = source.load_entries()

    assert len(entries) == 1
    assert entries[0].name == "Skeleton"
    assert entries[0].entry_type == CompendiumEntryType.MONSTER
    assert entries[0].page == 272


def test_data_source_summary_reports_missing_root_without_failure(tmp_path):
    source = FiveEToolsDataSource(raw_root=tmp_path / "missing")

    summary = source.load_summary()

    assert summary.missing_root is True
    assert summary.files_scanned == 0
    assert summary.collections_found == 0
    assert summary.entries_loaded == 0
    assert summary.ok is True


def test_data_source_records_invalid_json_errors(tmp_path):
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    (raw_root / "bad.json").write_text("not-json", encoding="utf-8")

    source = FiveEToolsDataSource(raw_root=raw_root)
    entries = source.load_entries()
    summary = source.load_summary()

    assert entries == []
    assert summary.errors
    assert summary.ok is False
