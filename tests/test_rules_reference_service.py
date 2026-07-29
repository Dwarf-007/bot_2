from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.rules_reference_service import RulesReferenceService
from services.compendium.source_policy import SourcePolicy


def _index():
    return CompendiumIndexService([
        CompendiumEntry(
            entry_id="condition:grappled:phb",
            name="Grappled",
            entry_type=CompendiumEntryType.CONDITION,
            source="PHB",
            page=290,
            rules_version="2014",
            aliases=["grabbed"],
            summary="A grappled creature's speed becomes 0, and it cannot benefit from bonuses to speed.",
        ),
        CompendiumEntry(
            entry_id="rule:opportunity-attack:phb",
            name="Opportunity Attack",
            entry_type=CompendiumEntryType.RULE,
            source="PHB",
            rules_version="2014",
            raw={"entries": ["You can make an opportunity attack when a hostile creature that you can see moves out of your reach."]},
        ),
        CompendiumEntry(
            entry_id="spell:fireball:phb",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source="PHB",
            rules_version="2014",
            summary="A spell, not a rule result for this service.",
        ),
    ])


def test_rules_reference_service_finds_condition_and_builds_advisory_text():
    service = RulesReferenceService(_index())

    result = service.lookup("Grappled")

    assert result.found is True
    assert result.matches[0].name == "Grappled"
    assert result.matches[0].entry_type == "condition"
    assert result.matches[0].source == "PHB"
    assert result.matches[0].page == 290
    assert "speed becomes 0" in result.matches[0].snippet
    assert "Talált szabályreferencia: Grappled" in result.advisory_text
    assert "DM-é" in result.advisory_text


def test_rules_reference_service_finds_alias():
    service = RulesReferenceService(_index())

    result = service.lookup("grabbed")

    assert result.found is True
    assert result.matches[0].name == "Grappled"
    assert result.matches[0].match_reason == "exact_alias"


def test_rules_reference_service_excludes_non_rule_entry_types():
    service = RulesReferenceService(_index())

    result = service.lookup("Fireball")

    assert result.found is False
    assert result.matches == []


def test_rules_reference_service_uses_source_policy():
    service = RulesReferenceService(
        _index(),
        source_policy=SourcePolicy(allowed_sources=["PHB"], allow_homebrew=False, rules_version="2014"),
    )

    result = service.lookup("Opportunity Attack")

    assert result.found is True
    assert result.matches[0].name == "Opportunity Attack"


def test_rules_reference_service_empty_query_is_safe():
    service = RulesReferenceService(_index())

    result = service.lookup("   ")

    assert result.found is False
    assert "Nem kaptam" in result.advisory_text


def test_rules_reference_service_truncates_long_raw_entries():
    long_text = "word " * 200
    index = CompendiumIndexService([
        CompendiumEntry(
            entry_id="rule:long",
            name="Long Rule",
            entry_type=CompendiumEntryType.RULE,
            raw={"entries": [long_text]},
        )
    ])
    service = RulesReferenceService(index, max_snippet_chars=80)

    result = service.lookup("Long Rule")

    assert result.found is True
    assert len(result.matches[0].snippet) <= 80
    assert result.matches[0].snippet.endswith("…")
