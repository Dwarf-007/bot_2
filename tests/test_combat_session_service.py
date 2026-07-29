from services.combat_session_service import CombatSessionService


class FakeBestiary:
    def get_monster_stats(self, name):
        if name == "Goblin":
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
        return None


def test_start_combat_session_builds_monsters_and_filters_non_monsters():
    service = CombatSessionService(bestiary_service=FakeBestiary())

    result = service.start_combat_session(
        channel_id="c1",
        monsters_data=["--", "Treasure: 10 gp", "2 x Goblin (cr 1/4)"],
    )

    assert result.ok is True
    assert result.state is not None
    assert result.state.active is True
    assert sorted(result.state.monsters.keys()) == ["Goblin 1", "Goblin 2"]
    assert result.state.monsters["Goblin 1"].current_hp == 7
    assert len(result.state.initiative_order) == 2


def test_start_combat_session_rejects_active_combat():
    service = CombatSessionService(bestiary_service=FakeBestiary())
    first = service.start_combat_session("c1", [{"name": "Goblin", "count": 1}])
    second = service.start_combat_session("c1", [{"name": "Goblin", "count": 1}])

    assert first.ok is True
    assert second.ok is False
    assert second.reason == "active_combat_exists"


def test_player_ac_and_roll_feedback_are_stored_on_session():
    service = CombatSessionService(bestiary_service=FakeBestiary())
    service.start_combat_session("c1", [{"name": "Goblin", "count": 1}])

    service.set_player_ac("c1", "p1", 15)
    service.append_player_roll("c1", "Alice", "1d20+5", 17)

    state = service.get_combat_state("c1")
    assert state.player_ac == {"p1": 15}
    assert state.player_rolls == [{"actor": "Alice", "formula": "1d20+5", "total": 17}]
