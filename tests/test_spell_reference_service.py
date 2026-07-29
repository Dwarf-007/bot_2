from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.source_policy import SourcePolicy
from services.compendium.spell_reference_service import SpellReferenceService


def _index():
    return CompendiumIndexService([
        CompendiumEntry(
            entry_id="spell:fireball:phb",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source="PHB",
            page=241,
            rules_version="2014",
            aliases=["classic fireball"],
            tags=["spell", "level:3", "school:V"],
            raw={
                "name": "Fireball",
                "source": "PHB",
                "page": 241,
                "level": 3,
                "school": "V",
                "time": [{"number": 1, "unit": "action"}],
                "range": {"type": "point", "distance": {"amount": 150, "type": "feet"}},
                "duration": [{"type": "instant"}],
                "components": {"v": True, "s": True, "m": "a tiny ball of bat guano and sulfur"},
                "classes": {"fromClassList": [{"name": "Sorcerer"}, {"name": "Wizard"}]},
                "entries": ["A bright streak flashes from your pointing finger to a point you choose."]
            },
        ),
        CompendiumEntry(
            entry_id="spell:mage-hand:phb",
            name="Mage Hand",
            entry_type=CompendiumEntryType.SPELL,
            source="PHB",
            rules_version="2014",
            tags=["spell", "level:0", "school:C"],
            raw={"level": 0, "school": "C", "entries": ["A spectral, floating hand appears."]},
        ),
        CompendiumEntry(
            entry_id="rule:fireball-like",
            name="Fireball Rule",
            entry_type=CompendiumEntryType.RULE,
            source="HB",
            summary="Not a spell.",
        ),
    ])


def test_spell_reference_service_finds_spell_and_extracts_metadata():
    service = SpellReferenceService(_index())

    result = service.lookup("Fireball")

    assert result.found is True
    match = result.matches[0]
    assert match.name == "Fireball"
    assert match.source == "PHB"
    assert match.page == 241
    assert match.level == 3
    assert match.school == "V"
    assert match.casting_time == "1 action"
    assert match.range_text == "150 feet"
    assert match.duration == "instant"
    assert "V" in match.components
    assert "S" in match.components
    assert "M (a tiny ball" in match.components
    assert match.classes == ["Sorcerer", "Wizard"]
    assert "bright streak" in match.snippet
    assert "Talált varázslatreferencia: Fireball" in result.advisory_text
    assert "DM-é" in result.advisory_text


def test_spell_reference_service_finds_alias():
    service = SpellReferenceService(_index())

    result = service.lookup("classic fireball")

    assert result.found is True
    assert result.matches[0].name == "Fireball"
    assert result.matches[0].match_reason == "exact_alias"


def test_spell_reference_service_excludes_non_spell_entry_types():
    service = SpellReferenceService(_index())

    result = service.lookup("Fireball Rule")

    assert result.found is False
    assert result.matches == []


def test_spell_reference_service_level_filter():
    service = SpellReferenceService(_index())

    result = service.lookup("Fireball", level=3)
    wrong_level = service.lookup("Fireball", level=1)

    assert result.found is True
    assert result.matches[0].name == "Fireball"
    assert wrong_level.found is False


def test_spell_reference_service_lookup_by_level_uses_tags():
    service = SpellReferenceService(_index())

    result = service.lookup_by_level(0)

    assert result.found is True
    assert result.matches[0].name == "Mage Hand"
    assert result.matches[0].level == 0
    assert "cantrip" in result.advisory_text


def test_spell_reference_service_source_policy():
    service = SpellReferenceService(
        _index(),
        source_policy=SourcePolicy(allowed_sources=["PHB"], allow_homebrew=False, rules_version="2014"),
    )

    result = service.lookup("Fireball")

    assert result.found is True
    assert result.matches[0].source == "PHB"


def test_spell_reference_service_empty_query_is_safe():
    service = SpellReferenceService(_index())

    result = service.lookup("   ")

    assert result.found is False
    assert "Nem kaptam" in result.advisory_text


def test_spell_reference_service_truncates_long_entries():
    long_text = "spark " * 200
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="spell:long",
            name="Long Spell",
            entry_type=CompendiumEntryType.SPELL,
            raw={"level": 1, "entries": [long_text]},
        )
    ])
    service = SpellReferenceService(index, max_snippet_chars=80)

    result = service.lookup("Long Spell")

    assert result.found is True
    assert len(result.matches[0].snippet) <= 80
    assert result.matches[0].snippet.endswith("…")
