from __future__ import annotations

from avrae.avrae_parser import AvraeParserService


def test_extract_roll_results_player_roll():
    text = "Alice rolls 1d20+5 = 17 for her attack."
    results = AvraeParserService.extract_roll_results(text)

    assert len(results) == 1
    assert results[0]["actor"] == "Alice"
    assert results[0]["formula"] == "1d20+5"
    assert results[0]["total"] == 17


def test_extract_roll_results_monster_roll():
    text = "Goblin 1 rolled 1d20+4 = 12"
    results = AvraeParserService.extract_roll_results(text)

    assert len(results) == 1
    assert results[0]["actor"] == "Goblin 1"
    assert results[0]["formula"] == "1d20+4"
    assert results[0]["total"] == 12
