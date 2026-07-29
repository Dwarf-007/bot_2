from core.encounter_models import EncounterResult, EncounterUnit
from services.encounter_service import EncounterService


class FakeCombatFeedbackService:
    def __init__(self):
        self.registered = None

    def register_encounter(self, **kwargs):
        self.registered = kwargs


def test_prepare_resolved_encounter_uses_suggested_commands_not_legacy_avrae_commands():
    feedback = FakeCombatFeedbackService()
    service = EncounterService(combat_feedback_service=feedback)
    encounter = EncounterResult(
        encounter_type="STATIC_ROOM",
        difficulty="STANDARD",
        units=[EncounterUnit(monster_name="Skeleton", count=2, source="ROOM")],
        room_id="room-1",
        trigger_reason="test",
        narrative_hint="Harc kezdődik.",
    )

    output = service.prepare_resolved_encounter(
        channel_id="c1",
        encounter=encounter,
        xp_reward_total=100,
    )

    assert output.avrae_commands == []
    assert output.suggested_commands == ["!init begin", "!init add Skeleton 2"]
    assert output.dm_instructions
    assert feedback.registered["channel_id"] == "c1"
    assert feedback.registered["room_id"] == "room-1"
    assert feedback.registered["monsters"] == [{"name": "Skeleton", "count": 2}]
    assert feedback.registered["xp_reward_total"] == 100


def test_prepare_resolved_encounter_without_units_has_no_suggested_commands():
    service = EncounterService()
    encounter = EncounterResult(
        encounter_type="STATIC_ROOM",
        difficulty="STANDARD",
        units=[],
        room_id="room-1",
        trigger_reason="test",
        narrative_hint="",
    )

    output = service.prepare_resolved_encounter(channel_id="c1", encounter=encounter)

    assert output.avrae_commands == []
    assert output.suggested_commands == []
    assert output.dm_instructions == []
    assert output.debug_notes
