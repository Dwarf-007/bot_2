from core.turn_output import TurnOutput
from services.combat_start_service import CombatStartService


class FakeEncounterService:
    def __init__(self):
        self.calls = []

    def prepare_resolved_encounter(self, *, channel_id, encounter, xp_reward_total=0):
        self.calls.append({
            "channel_id": channel_id,
            "encounter": encounter,
            "xp_reward_total": xp_reward_total,
        })
        return TurnOutput(
            suggested_commands=["!init begin", "!init add Skeleton 2"],
            dm_instructions=["Encounter előkészítve."],
        )


def test_combat_start_service_preserves_advisory_suggested_commands():
    encounter_service = FakeEncounterService()
    service = CombatStartService(encounter_service)

    output = service.start_combat(
        channel_id="c1",
        room_id="room-1",
        monsters=[{"name": "Skeleton", "count": 2}],
        xp_reward_total=100,
        narrative="A csontvázak támadnak!",
    )

    assert output.public_narrative == "A csontvázak támadnak!"
    assert output.avrae_commands == []
    assert output.suggested_commands == ["!init begin", "!init add Skeleton 2"]
    assert any("nem futnak automatikusan" in item or "manuálisan" in item for item in output.dm_instructions)
    assert encounter_service.calls[0]["channel_id"] == "c1"
    assert encounter_service.calls[0]["xp_reward_total"] == 100
    assert encounter_service.calls[0]["encounter"].room_id == "room-1"
