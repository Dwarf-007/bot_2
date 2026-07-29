from pathlib import Path

from avrae.avrae_command_builder import AvraeCommandBuilder


def test_avrae_command_builder_has_no_dispatch_or_io_calls():
    text = Path("avrae/avrae_command_builder.py").read_text(encoding="utf-8")

    forbidden = [
        "dispatch_commands",
        "AvraeDispatcher",
        "AvraeClient",
        "message.channel.send",
        "requests.",
        "urlopen",
    ]
    for marker in forbidden:
        assert marker not in text


def test_avrae_command_builder_still_formats_init_commands_from_monsters():
    commands = AvraeCommandBuilder.build_init_commands_from_monsters([
        {"name": "Goblin", "count": 2},
        {"name": "Skeleton", "count": "1"},
    ])

    assert commands == ["!init begin", "!init add Goblin 2", "!init add Skeleton 1"]
