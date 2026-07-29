from services.compendium.compendium_models import (
    CompendiumEntry,
    CompendiumEntryType,
    CompendiumQuery,
    CompendiumSearchResult,
)
from services.compendium.source_policy import SourcePolicy


def test_compendium_entry_normalized_matching_supports_name_alias_and_partial_name():
    entry = CompendiumEntry(
        entry_id="monster:goblin:mm",
        name="Goblin",
        entry_type=CompendiumEntryType.MONSTER,
        source_system="5etools",
        source="MM",
        aliases=["gob"],
    )

    assert entry.normalized_name() == "goblin"
    assert entry.matches_text("Goblin") is True
    assert entry.matches_text("gob") is True
    assert entry.matches_text("gobl") is True
    assert entry.matches_text("") is False


def test_compendium_query_normalization():
    query = CompendiumQuery(
        text="  Fireball ",
        entry_types=[CompendiumEntryType.SPELL, "rule"],
        allowed_sources=["PHB", " XGE "],
        rules_version="2014",
        limit=3,
    )

    assert query.normalized_text() == "fireball"
    assert query.normalized_entry_types() == ["spell", "rule"]
    assert query.normalized_allowed_sources() == ["phb", "xge"]
    assert query.limit == 3


def test_compendium_search_result_exact_match_helper():
    entry = CompendiumEntry(entry_id="spell:fireball:phb", name="Fireball", entry_type=CompendiumEntryType.SPELL)

    exact = CompendiumSearchResult(entry=entry, score=1.0, match_reason="exact_name")
    fuzzy = CompendiumSearchResult(entry=entry, score=0.5, match_reason="contains_name")

    assert exact.is_exact_match() is True
    assert fuzzy.is_exact_match() is False


def test_source_policy_filters_allowed_sources_rules_version_and_homebrew():
    entries = [
        CompendiumEntry(
            entry_id="spell:fireball:phb",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source_system="5etools",
            source="PHB",
            rules_version="2014",
        ),
        CompendiumEntry(
            entry_id="spell:homebrew-blast",
            name="Homebrew Blast",
            entry_type=CompendiumEntryType.SPELL,
            source_system="homebrew",
            source="HB",
            rules_version="2014",
        ),
        CompendiumEntry(
            entry_id="spell:new-fireball:phb2024",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source_system="5etools",
            source="PHB2024",
            rules_version="2024",
        ),
    ]

    policy = SourcePolicy(allowed_sources=["PHB"], allow_homebrew=False, rules_version="2014")

    filtered = policy.filter_entries(entries)

    assert [entry.entry_id for entry in filtered] == ["spell:fireball:phb"]


def test_source_policy_blocked_source_wins():
    entry = CompendiumEntry(
        entry_id="item:example",
        name="Example Item",
        entry_type=CompendiumEntryType.ITEM,
        source="DMG",
    )

    policy = SourcePolicy(allowed_sources=["DMG"], blocked_sources=["DMG"])

    assert policy.allows(entry) is False
