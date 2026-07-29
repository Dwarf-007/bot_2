import pytest

from avrae.avrae_command_builder import AvraeCommandBuilder


def test_build_init_from_monsters_single():
    cmds = AvraeCommandBuilder.build_init_commands_from_monsters([
        {"name": "Goblin", "n": 1}
    ])
    assert cmds[0] == "!init begin"
    assert any("-name Goblin" in c for c in cmds[1:])
    assert any("-n 1" in c for c in cmds[1:])


def test_build_init_with_autonumber_and_count():
    cmds = AvraeCommandBuilder.build_init_commands_from_monsters([
        {"name": "Orc#", "n": 3}
    ])
    assert cmds[0] == "!init begin"
    # Should include both name and count flags
    assert any("-name Orc#" in c for c in cmds[1:])
    assert any("-n 3" in c for c in cmds[1:])


def test_build_check_and_save_commands():
    check = AvraeCommandBuilder.build_check_command("perception", dc=12)
    assert check == "!check perception -dc 12"

    save = AvraeCommandBuilder.build_check_command("dex save", dc=15, is_save=True)
    # Normalized: drops the word 'save' and emits !save
    assert save == "!save dex -dc 15"


def test_build_damage_command():
    dmg = AvraeCommandBuilder.build_damage_command("goblin1", 7, "slashing")
    assert dmg == "!damage goblin1 7 slashing"

    dmg_no_type = AvraeCommandBuilder.build_damage_command("goblin1", 5, None)
    assert dmg_no_type == "!damage goblin1 5"
