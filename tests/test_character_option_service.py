from services.compendium.character_option_service import CharacterOptionService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType


def _index():
    return CompendiumIndexService([
        CompendiumEntry(
            entry_id="class:fighter:phb",
            name="Fighter",
            entry_type=CompendiumEntryType.CLASS,
            source="PHB",
            summary="A master of martial combat.",
            raw={
                "name": "Fighter",
                "classFeatures": [
                    {"name": "Ability Score Improvement", "level": 4, "entries": ["You can increase ability scores or choose a feat."]},
                    {"name": "Extra Attack", "level": 5, "entries": ["You can attack twice when you take the Attack action."]},
                ],
            },
        ),
        CompendiumEntry(
            entry_id="rule:action-surge:fighter:phb:2",
            name="Action Surge",
            entry_type=CompendiumEntryType.RULE,
            source="PHB",
            raw={"name": "Action Surge", "className": "Fighter", "level": 2, "entries": ["Take one additional action."]},
        ),
        CompendiumEntry(
            entry_id="species:human:phb",
            name="Human",
            entry_type=CompendiumEntryType.SPECIES,
            source="PHB",
            summary="A versatile species.",
        ),
        CompendiumEntry(
            entry_id="background:soldier:phb",
            name="Soldier",
            entry_type=CompendiumEntryType.BACKGROUND,
            source="PHB",
            summary="A military background.",
        ),
        CompendiumEntry(
            entry_id="feat:alert:phb",
            name="Alert",
            entry_type=CompendiumEntryType.FEAT,
            source="PHB",
            summary="Always on the lookout for danger.",
        ),
    ])


def test_character_option_service_lookup_specific_option_types():
    service = CharacterOptionService(_index())

    assert service.lookup_class("Fighter").matches[0].entry_type == "class"
    assert service.lookup_species("Human").matches[0].entry_type == "species"
    assert service.lookup_background("Soldier").matches[0].entry_type == "background"
    assert service.lookup_feat("Alert").matches[0].entry_type == "feat"


def test_character_option_service_get_class_level_features_from_class_raw():
    service = CharacterOptionService(_index())

    result = service.get_class_level_features("Fighter", 5)

    assert result.found is True
    assert result.features[0].name == "Extra Attack"
    assert result.features[0].level == 5
    assert "attack twice" in result.features[0].snippet


def test_character_option_service_get_class_level_features_from_indexed_feature_entries():
    service = CharacterOptionService(_index())

    result = service.get_class_level_features("Fighter", 2)

    assert result.found is True
    assert result.features[0].name == "Action Surge"
    assert result.features[0].level == 2
    assert "additional action" in result.features[0].snippet


def test_character_option_service_empty_query_is_safe():
    service = CharacterOptionService(_index())

    result = service.lookup_option("   ")

    assert result.found is False
    assert "Nem kaptam" in result.advisory_text
