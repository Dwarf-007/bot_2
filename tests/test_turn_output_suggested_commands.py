from core.turn_output import TurnOutput


def test_turn_output_existing_defaults_are_preserved():
    output = TurnOutput(public_narrative="A terem ajtaja lassan kinyílik.")

    assert output.public_narrative == "A terem ajtaja lassan kinyílik."
    assert output.avrae_commands == []
    assert output.secret_messages == []
    assert output.debug_notes == []
    assert output.state_changed is False
    assert output.next_room_id is None
    assert output.dm_instructions == []
    assert output.suggested_commands == []
    assert output.has_dm_guidance() is False


def test_turn_output_can_carry_dm_instructions_and_suggested_commands():
    output = TurnOutput(
        public_narrative="A csontvázak előlépnek a kripta árnyékából.",
        dm_instructions=["Indítsd el a harcot Avrae-ban, ha a party felveszi a harcot."],
        suggested_commands=["!init begin", "!init add Skeleton 1", "!init add Skeleton 2"],
    )

    assert output.has_dm_guidance() is True
    assert output.dm_instructions == ["Indítsd el a harcot Avrae-ban, ha a party felveszi a harcot."]
    assert output.suggested_commands == ["!init begin", "!init add Skeleton 1", "!init add Skeleton 2"]
    assert output.all_suggested_commands() == ["!init begin", "!init add Skeleton 1", "!init add Skeleton 2"]


def test_turn_output_merges_legacy_avrae_commands_without_duplicates():
    output = TurnOutput(
        suggested_commands=["!init begin", "!init add Goblin 1"],
        avrae_commands=["!init begin", "!init add Goblin 2"],
    )

    assert output.has_dm_guidance() is True
    assert output.all_suggested_commands() == ["!init begin", "!init add Goblin 1", "!init add Goblin 2"]
