import json
from pathlib import Path

from tools.import_5etools_bestiary import normalize_bestiary


def test_normalize_bestiary_minimal():
    source = [
        {
            "name": "Goblin",
            "hp": {"average": 7},
            "ac": 15,
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 200,
            "challenge_rating": "1/4",
        }
    ]

    normalized = normalize_bestiary(source)
    assert "monster" in normalized
    assert isinstance(normalized["monster"], list)
    assert normalized["monster"][0]["name"] == "Goblin"
    assert normalized["monster"][0]["hp"]["average"] == 7
    assert normalized["monster"][0]["ac"] == 15
    assert normalized["monster"][0]["attack_bonus"] == 4
    assert normalized["monster"][0]["damage"] == "1d6+2"
    assert normalized["monster"][0]["xp"] == 200
