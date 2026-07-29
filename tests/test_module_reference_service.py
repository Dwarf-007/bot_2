from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.module_reference_service import ModuleReferenceQuery, ModuleReferenceService


def _index():
    return CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:lost-mine:lmop",
            name="Lost Mine Sample",
            entry_type=CompendiumEntryType.ADVENTURE,
            source="LMOP",
            page=7,
            summary="A starter adventure about a lost mine and frontier town.",
            raw={
                "name": "Lost Mine Sample",
                "id": "LMOP",
                "entries": [
                    {"type": "section", "name": "Goblin Ambush", "entries": ["The trail narrows before goblins attack from hiding."]},
                    {"type": "section", "name": "Cragmaw Hideout", "entries": ["A cave hideout with wolves, goblins, and a stream."]},
                ],
            },
        ),
        CompendiumEntry(
            entry_id="book:phb",
            name="Player Handbook Sample",
            entry_type=CompendiumEntryType.BOOK,
            source="PHB",
            raw={"entries": [{"name": "Adventuring", "entries": ["Rules for exploration and adventuring."]}]},
        ),
    ])


def test_module_reference_service_finds_adventure_by_entry_name():
    service = ModuleReferenceService(_index())

    result = service.lookup("Lost Mine")

    assert result.found is True
    assert result.matches[0].name == "Lost Mine Sample"
    assert result.matches[0].source == "LMOP"
    assert "starter adventure" in result.matches[0].snippet
    assert result.dm_review_recommended is True
    assert "DM review recommended" in result.advisory_text


def test_module_reference_service_finds_nested_section():
    service = ModuleReferenceService(_index())

    result = service.lookup("Cragmaw Hideout")

    assert result.found is True
    assert result.matches[0].name == "Cragmaw Hideout"
    assert result.matches[0].path_text == "Lost Mine Sample > Cragmaw Hideout"
    assert "cave hideout" in result.matches[0].snippet
    assert "Automation hint" in result.advisory_text


def test_module_reference_service_lookup_section_filters_module_name():
    service = ModuleReferenceService(_index())

    result = service.lookup_section("lost mine", "Goblin Ambush")

    assert result.found is True
    assert result.matches[0].name == "Goblin Ambush"
    assert "goblins attack" in result.matches[0].snippet


def test_module_reference_service_empty_query_is_safe():
    service = ModuleReferenceService(_index())

    result = service.lookup("   ")

    assert result.found is False
    assert "Nem kaptam" in result.advisory_text


def test_module_reference_service_truncates_long_text():
    long_text = "campaign secret " * 200
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="adventure:long",
            name="Long Adventure",
            entry_type=CompendiumEntryType.ADVENTURE,
            raw={"entries": [{"name": "Long Room", "entries": [long_text]}]},
        )
    ])
    service = ModuleReferenceService(index, max_snippet_chars=120)

    result = service.lookup(ModuleReferenceQuery(text="Long Room", max_snippet_chars=120))

    assert result.found is True
    assert len(result.matches[0].snippet) <= 120
    assert result.matches[0].snippet.endswith("…")
