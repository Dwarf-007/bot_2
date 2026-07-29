import json

from services.compendium.compendium_models import CompendiumEntryType
from services.compendium.fiveetools_data_source import FiveEToolsDataSource
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.spell_reference_service import SpellReferenceService


def test_spell_reference_service_can_use_fiveetools_spell_raw_file(tmp_path):
    raw_root = tmp_path / "raw"
    spell_dir = raw_root / "spells"
    spell_dir.mkdir(parents=True)
    (spell_dir / "spells-phb.json").write_text(
        json.dumps({
            "spell": [
                {
                    "name": "Fireball",
                    "source": "PHB",
                    "page": 241,
                    "level": 3,
                    "school": "V",
                    "time": [{"number": 1, "unit": "action"}],
                    "range": {"type": "point", "distance": {"amount": 150, "type": "feet"}},
                    "duration": [{"type": "instant"}],
                    "components": {"v": True, "s": True, "m": "a tiny ball of bat guano and sulfur"},
                    "entries": ["A bright streak flashes from your pointing finger."]
                }
            ]
        }),
        encoding="utf-8",
    )

    entries = FiveEToolsDataSource(raw_root=raw_root).load_entries(entry_types=[CompendiumEntryType.SPELL])
    service = SpellReferenceService(CompendiumIndexService(entries))

    result = service.lookup("Fireball")

    assert result.found is True
    assert result.matches[0].entry_id == "spell:fireball:phb"
    assert result.matches[0].level == 3
    assert result.matches[0].range_text == "150 feet"
    assert "bright streak" in result.matches[0].snippet
