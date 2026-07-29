from services.runtime_visibility_intents import RuntimeVisibilityIntentParser


def test_look_hu():
    p = RuntimeVisibilityIntentParser()
    assert p.parse('körülnézek').kind == 'LOOK'


def test_move_hu():
    p = RuntimeVisibilityIntentParser()
    got = p.parse('megyünk keletre')
    assert got.kind == 'MOVE'
    assert got.direction == 'east'


def test_secret():
    p = RuntimeVisibilityIntentParser()
    got = p.parse('rejtett ajtót keresek')
    assert got.kind == 'SEARCH_SECRET'
