import json

from services.compendium.compendium_models import CompendiumEntryType
from services.compendium.fiveetools_data_source import FiveEToolsDataSource


def test_data_source_loads_rule_like_top_level_json_files(tmp_path):
    raw_root = tmp_path / "raw"
    rules_dir = raw_root / "rules"
    conditions_dir = raw_root / "conditions"
    rules_dir.mkdir(parents=True)
    conditions_dir.mkdir(parents=True)

    (rules_dir / "actions.json").write_text(
        json.dumps({
            "action": [
                {"name": "Dash", "source": "PHB", "entries": ["When you take the Dash action, you gain extra movement."]}
            ]
        }),
        encoding="utf-8",
    )
    (conditions_dir / "conditionsdiseases.json").write_text(
        json.dumps({
            "condition": [
                {"name": "Poisoned", "source": "PHB", "entries": ["A poisoned creature has disadvantage on attack rolls and ability checks."]}
            ],
            "disease": [
                {"name": "Example Disease", "source": "DMG", "entries": ["A sample disease entry."]}
            ],
        }),
        encoding="utf-8",
    )

    source = FiveEToolsDataSource(raw_root=raw_root)
    entries = source.load_entries()
    by_name = {entry.name: entry for entry in entries}

    assert by_name["Dash"].entry_type == CompendiumEntryType.RULE
    assert by_name["Poisoned"].entry_type == CompendiumEntryType.CONDITION
    assert by_name["Example Disease"].entry_type == CompendiumEntryType.CONDITION
    assert "action" in by_name["Dash"].tags
    assert "condition" in by_name["Poisoned"].tags
    assert "disease" in by_name["Example Disease"].tags
