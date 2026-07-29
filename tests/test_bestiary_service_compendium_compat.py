import json

from services.bestiary_service import BestiaryService
from services.compendium.compendium_index_service import CompendiumIndexService
from services.compendium.compendium_models import CompendiumEntry, CompendiumEntryType
from services.compendium.source_policy import SourcePolicy


def test_bestiary_service_legacy_json_behavior_is_preserved(tmp_path):
    bestiary_file = tmp_path / "bestiary.json"
    bestiary_file.write_text(
        json.dumps({
            "monster": [
                {
                    "name": "Goblin",
                    "hp": {"average": 7},
                    "ac": 15,
                    "attack_bonus": 4,
                    "damage": "1d6+2",
                    "xp": 50,
                }
            ]
        }),
        encoding="utf-8",
    )

    service = BestiaryService(path=str(bestiary_file))

    assert service.is_loaded is True
    assert service.is_compendium_backed is False
    assert service.get_monster_stats("Goblin")["hp"]["average"] == 7
    assert service.get_monster_stats("gobl")["name"] == "Goblin"


def test_bestiary_service_prefers_compendium_when_configured(tmp_path):
    bestiary_file = tmp_path / "bestiary.json"
    bestiary_file.write_text(
        json.dumps({
            "monster": [
                {"name": "Goblin", "hp": {"average": 1}, "ac": 10, "attack_bonus": 1, "damage": "1d4", "xp": 10}
            ]
        }),
        encoding="utf-8",
    )
    entry = CompendiumEntry(
        entry_id="monster:goblin:mm",
        name="Goblin",
        entry_type=CompendiumEntryType.MONSTER,
        source_system="5etools",
        source="MM",
        raw={
            "name": "Goblin",
            "hp": {"average": 7},
            "ac": 15,
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
        },
    )
    index = CompendiumIndexService([entry])

    service = BestiaryService(path=str(bestiary_file), compendium_index=index)

    stats = service.get_monster_stats("Goblin")
    assert stats["hp"]["average"] == 7
    assert stats["attack_bonus"] == 4
    assert service.is_compendium_backed is True


def test_bestiary_service_can_prefer_legacy_when_requested(tmp_path):
    bestiary_file = tmp_path / "bestiary.json"
    bestiary_file.write_text(
        json.dumps({
            "monster": [
                {"name": "Goblin", "hp": {"average": 9}, "ac": 12, "attack_bonus": 3, "damage": "1d6", "xp": 25}
            ]
        }),
        encoding="utf-8",
    )
    entry = CompendiumEntry(
        entry_id="monster:goblin:mm",
        name="Goblin",
        entry_type=CompendiumEntryType.MONSTER,
        source="MM",
        raw={"name": "Goblin", "hp": {"average": 7}, "ac": 15, "attack_bonus": 4, "damage": "1d6+2", "xp": 50},
    )

    service = BestiaryService(
        path=str(bestiary_file),
        compendium_index=CompendiumIndexService([entry]),
        prefer_compendium=False,
    )

    stats = service.get_monster_stats("Goblin")
    assert stats["hp"]["average"] == 9
    assert stats["attack_bonus"] == 3


def test_bestiary_service_normalizes_raw_compendium_monster_for_combat_compatibility():
    entry = CompendiumEntry(
        entry_id="monster:goblin:mm",
        name="Goblin",
        entry_type=CompendiumEntryType.MONSTER,
        source_system="5etools",
        source="MM",
        rules_version="2014",
        raw={
            "name": "Goblin",
            "source": "MM",
            "hp": {"average": 7},
            "ac": [{"value": 15}],
            "cr": "1/4",
            "action": [
                {"name": "Scimitar", "desc": "Melee Weapon Attack: +4 to hit. Hit: 1d6+2 slashing damage."}
            ],
        },
    )
    service = BestiaryService(compendium_index=CompendiumIndexService([entry]))

    stats = service.get_monster_stats("Goblin")

    assert stats["name"] == "Goblin"
    assert stats["hp"]["average"] == 7
    assert stats["ac"] == 15
    assert stats["attack_bonus"] == 4
    assert stats["damage"] == "1d6+2"
    assert stats["xp"] == 50
    assert stats["challenge_rating"] == "1/4"
    assert stats["source"] == "MM"
    assert stats["source_system"] == "5etools"
    assert stats["rules_version"] == "2014"


def test_bestiary_service_can_build_compendium_index_from_raw_root(tmp_path):
    raw_root = tmp_path / "raw"
    monster_dir = raw_root / "monsters"
    monster_dir.mkdir(parents=True)
    (monster_dir / "bestiary-mm.json").write_text(
        json.dumps({
            "monster": [
                {"name": "Skeleton", "source": "MM", "hp": {"average": 13}, "ac": 13, "cr": "1/4"}
            ]
        }),
        encoding="utf-8",
    )

    service = BestiaryService(compendium_raw_root=raw_root)

    stats = service.get_monster_stats("Skeleton")
    assert service.is_loaded is True
    assert service.is_compendium_backed is True
    assert stats["name"] == "Skeleton"
    assert stats["hp"]["average"] == 13
    assert stats["xp"] == 50


def test_bestiary_service_source_policy_filters_compendium_results():
    entries = [
        CompendiumEntry(
            entry_id="monster:goblin:mm",
            name="Goblin",
            entry_type=CompendiumEntryType.MONSTER,
            source="MM",
            rules_version="2014",
            raw={"name": "Goblin", "hp": {"average": 7}, "ac": 15, "attack_bonus": 4, "damage": "1d6+2"},
        ),
        CompendiumEntry(
            entry_id="monster:goblin:hb",
            name="Goblin",
            entry_type=CompendiumEntryType.MONSTER,
            source_system="homebrew",
            source="HB",
            rules_version="2014",
            raw={"name": "Goblin", "hp": {"average": 20}, "ac": 99, "attack_bonus": 9, "damage": "2d6"},
        ),
    ]
    service = BestiaryService(
        compendium_index=CompendiumIndexService(entries),
        source_policy=SourcePolicy(allowed_sources=["MM"], allow_homebrew=False, rules_version="2014"),
    )

    stats = service.get_monster_stats("Goblin")
    assert stats["hp"]["average"] == 7
    assert stats["ac"] == 15
