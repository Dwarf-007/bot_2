from services.combat_dice_service import CombatDiceService


def test_roll_d20_plus_returns_value_in_expected_range():
    dice = CombatDiceService()

    for _ in range(100):
        value = dice.roll_d20_plus(4)
        assert 5 <= value <= 24


def test_roll_damage_supports_simple_dice_notation():
    dice = CombatDiceService()

    for _ in range(100):
        value = dice.roll_damage("1d6+2")
        assert 3 <= value <= 8


def test_roll_damage_returns_one_for_unsupported_input():
    dice = CombatDiceService()

    assert dice.roll_damage("not-a-die") == 1
    assert dice.roll_damage("") == 1
