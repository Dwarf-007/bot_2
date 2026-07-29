from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType, CompendiumQuery
from services.compendium.source_policy import SourcePolicy


def _entries():
    return [
        CompendiumEntry(
            entry_id="monster:goblin:mm",
            name="Goblin",
            entry_type=CompendiumEntryType.MONSTER,
            source_system="5etools",
            source="MM",
            rules_version="2014",
            aliases=["gob"],
            tags=["monster", "cr:1/4", "source:MM"],
            summary="A small sneaky humanoid monster.",
        ),
        CompendiumEntry(
            entry_id="spell:fireball:phb",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source_system="5etools",
            source="PHB",
            rules_version="2014",
            aliases=["classic fireball"],
            tags=["spell", "level:3", "school:V"],
            summary="A bright streak flashes and explodes.",
        ),
        CompendiumEntry(
            entry_id="spell:fireball:phb2024",
            name="Fireball",
            entry_type=CompendiumEntryType.SPELL,
            source_system="5etools",
            source="PHB2024",
            rules_version="2024",
            tags=["spell", "level:3"],
        ),
        CompendiumEntry(
            entry_id="spell:homebrew-blast",
            name="Homebrew Blast",
            entry_type=CompendiumEntryType.SPELL,
            source_system="homebrew",
            source="HB",
            rules_version="2014",
            tags=["spell", "homebrew"],
        ),
    ]


def test_index_exact_lookup_by_name_and_alias():
    index = CompendiumIndexService(_entries())

    exact = index.lookup_exact("Goblin")
    alias = index.lookup_exact("gob")

    assert [entry.entry_id for entry in exact] == ["monster:goblin:mm"]
    assert [entry.entry_id for entry in alias] == ["monster:goblin:mm"]


def test_index_search_ranks_exact_name_before_contains_and_summary_matches():
    index = CompendiumIndexService(_entries())

    results = index.search(CompendiumQuery(text="Fireball", entry_types=[CompendiumEntryType.SPELL], limit=5))

    assert results[0].entry.entry_id in {"spell:fireball:phb", "spell:fireball:phb2024"}
    assert results[0].match_reason == "exact_name"
    assert all(result.entry.entry_type == CompendiumEntryType.SPELL for result in results)


def test_index_search_supports_source_policy_filtering():
    index = CompendiumIndexService(_entries())
    policy = SourcePolicy(allowed_sources=["PHB"], allow_homebrew=False, rules_version="2014")

    results = index.search(CompendiumQuery(text="Fireball", entry_types=[CompendiumEntryType.SPELL]), source_policy=policy)

    assert [result.entry.entry_id for result in results] == ["spell:fireball:phb"]


def test_index_search_uses_query_allowed_sources_when_no_explicit_policy_provided():
    index = CompendiumIndexService(_entries())
    query = CompendiumQuery(
        text="Fireball",
        entry_types=[CompendiumEntryType.SPELL],
        allowed_sources=["PHB2024"],
        rules_version="2024",
        include_homebrew=False,
    )

    results = index.search(query)

    assert [result.entry.entry_id for result in results] == ["spell:fireball:phb2024"]


def test_index_search_can_match_tags_and_summary():
    index = CompendiumIndexService(_entries())

    tag_results = index.search("cr:1/4")
    summary_results = index.search("sneaky")

    assert tag_results[0].entry.entry_id == "monster:goblin:mm"
    assert tag_results[0].match_reason == "tag_match"
    assert summary_results[0].entry.entry_id == "monster:goblin:mm"
    assert summary_results[0].match_reason == "summary_contains"


def test_index_stats_reports_entry_counts():
    index = CompendiumIndexService(_entries())

    stats = index.stats()

    assert stats.entries == 4
    assert stats.names == 3
    assert stats.entry_types["spell"] == 3
    assert stats.entry_types["monster"] == 1
    assert stats.aliases == 2


def test_index_add_entries_rebuilds_lookup_maps():
    index = CompendiumIndexService([])
    index.add_entries([_entries()[0]])

    assert index.lookup_exact("Goblin")
    assert index.get_by_id("monster:goblin:mm").name == "Goblin"
