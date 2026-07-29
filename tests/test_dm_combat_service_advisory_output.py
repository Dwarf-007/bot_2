from services.dm_combat_service import DMCombatService


class FakeLLM:
    def generate(self, prompt):
        return '{"action_index": 0, "target_id": "p1", "reason": "test"}'


class FakeBestiary:
    def get_monster_stats(self, name):
        return {
            "hp": {"average": 7},
            "ac": [13],
            "attack_bonus": 4,
            "damage": "1d6+2",
            "xp": 50,
            "action": [
                {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2"}
            ],
        }


class FailingDispatcher:
    def __init__(self):
        self.called = False

    def is_available(self):
        self.called = True
        return True

    def dispatch_commands(self, commands):
        self.called = True
        raise AssertionError("DMCombatService must not dispatch Avrae commands in C3.4")


def test_start_combat_returns_suggested_commands_without_dispatch():
    dispatcher = FailingDispatcher()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        avrae_dispatcher=dispatcher,
    )

    output = service.start_combat(
        channel_id="c1",
        monsters_data=[{"name": "Goblin", "count": 2}],
    )

    assert dispatcher.called is False
    assert output.avrae_commands == []
    assert output.suggested_commands[0] == "!init begin"
    assert "!init add 1 Goblin -hp 7" in output.suggested_commands
    assert output.dm_instructions
    assert "Harc kezdődik" in output.public_narrative


def test_execute_monster_turn_returns_advisory_roll_command_without_dispatch():
    dispatcher = FailingDispatcher()
    service = DMCombatService(
        llm_adapter=FakeLLM(),
        bestiary_service=FakeBestiary(),
        avrae_dispatcher=dispatcher,
    )
    service.start_combat(channel_id="c1", monsters_data=[{"name": "Goblin", "count": 1}])
    service.set_player_ac("c1", "p1", 12)

    output = service.execute_monster_turn("c1")

    assert dispatcher.called is False
    assert output is not None
    assert output.suggested_commands
    assert output.suggested_commands[0].startswith("!r 1d20+")
    assert output.dm_instructions
