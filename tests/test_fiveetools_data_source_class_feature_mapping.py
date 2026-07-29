import json

from services.compendium.compendium_models import CompendiumEntryType
from services.compendium.fiveetools_data_source import FiveEToolsDataSource


def test_data_source_loads_class_features_as_rule_entries(tmp_path):
    raw_root = tmp_path / "raw"
    class_dir = raw_root / "classes"
    class_dir.mkdir(parents=True)
    (class_dir / "class-fighter.json").write_text(
        json.dumps({
            "class": [{"name": "Fighter", "source": "PHB"}],
            "classFeature": [
                {"name": "Extra Attack", "source": "PHB", "className": "Fighter", "level": 5, "entries": ["Attack twice."]}
            ],
            "subclassFeature": [
                {"name": "Remarkable Athlete", "source": "PHB", "className": "Fighter", "subclassShortName": "Champion", "level": 7}
            ],
        }),
        encoding="utf-8",
    )

    entries = FiveEToolsDataSource(raw_root=raw_root).load_entries()
    by_name = {entry.name: entry for entry in entries}

    assert by_name["Fighter"].entry_type == CompendiumEntryType.CLASS
    assert by_name["Extra Attack"].entry_type == CompendiumEntryType.RULE
    assert by_name["Remarkable Athlete"].entry_type == CompendiumEntryType.RULE
    assert "classfeature" in by_name["Extra Attack"].tags
    assert "subclassfeature" in by_name["Remarkable Athlete"].tags
    assert "level:5" in by_name["Extra Attack"].tags
    assert "class:Fighter" in by_name["Extra Attack"].tags
