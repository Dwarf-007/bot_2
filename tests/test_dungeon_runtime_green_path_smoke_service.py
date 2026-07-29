from services.dungeon_runtime_green_path_smoke_service import DungeonRuntimeGreenPathSmokeService


class Out:
    def __init__(self, text):
        self.public_narrative = text


class FakeGameTurnService:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
    def process(self, channel_id, player_id, text, campaign_id_override=None):
        self.calls.append((text, campaign_id_override))
        return Out(self.outputs.pop(0) if self.outputs else "ok")


def test_green_path_smoke_passes_clean_outputs():
    svc = DungeonRuntimeGreenPathSmokeService(FakeGameTurnService(["look ok", "map ok", "move ok", "back ok", "full map ok", "search ok"]))
    result = svc.run(channel_id="ch", player_id="p", campaign_id_override="tenebrous")
    assert result.ok is True
    assert len(result.steps) == 6
    assert result.false_green is False


def test_green_path_move_rejects_ambiguity_prompt():
    svc = DungeonRuntimeGreenPathSmokeService(FakeGameTurnService(["look ok", "map ok", "Több továbbvezető folyosószakasz látszik. Válassz egy sorszámot.", "back ok", "full map ok", "search ok"]))
    result = svc.run(channel_id="ch", player_id="p", campaign_id_override="tenebrous")
    assert result.ok is False
    move_step = [s for s in result.steps if s.name == "move_choice"][0]
    assert move_step.ok is False
    assert "Forbidden green-path marker" in move_step.detected_issue


def test_green_path_back_rejects_no_history():
    svc = DungeonRuntimeGreenPathSmokeService(FakeGameTurnService(["look ok", "map ok", "move ok", "Nem egyértelmű, merre van vissza.", "full map ok", "search ok"]))
    result = svc.run(channel_id="ch", player_id="p", campaign_id_override="tenebrous")
    assert result.ok is False
    back_step = [s for s in result.steps if s.name == "back_after_move"][0]
    assert back_step.ok is False


def test_green_path_rejects_runtime_error():
    svc = DungeonRuntimeGreenPathSmokeService(FakeGameTurnService(["look ok", "A visibility runtime hibát jelzett: boom", "move ok", "back ok", "full map ok", "search ok"]))
    result = svc.run(channel_id="ch", player_id="p", campaign_id_override="tenebrous")
    assert result.ok is False
    assert result.steps[1].ok is False
