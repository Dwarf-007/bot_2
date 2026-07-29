import json
from pathlib import Path

from services.dungeon_runtime_path_history_auditor import DungeonRuntimePathHistoryAuditor


def pos(node_id, node_type="segment", room_id=None, segment_id=None, cell=(1, 1)):
    return {
        "node_id": node_id,
        "node_type": node_type,
        "level": 1,
        "room_id": room_id,
        "segment_id": segment_id if segment_id is not None else (node_id if node_type == "segment" else None),
        "cell": list(cell) if cell else None,
    }


def clean_state():
    return {
        "campaign_id": "tenebrous",
        "current": pos("s3"),
        "path_history": [pos("r1", "room", room_id="r1", segment_id=None, cell=None), pos("s1"), pos("s2")],
    }


def test_audit_clean_history_ok():
    result = DungeonRuntimePathHistoryAuditor().audit_state_dict(clean_state())
    assert result.ok is True
    assert result.status == "OK"
    assert result.path_history_count == 3
    assert result.valid_entries == 3
    assert result.unique_positions == 3
    assert result.current_equals_last_history is False


def test_audit_detects_current_equals_last_warning():
    data = clean_state()
    data["current"] = pos("s2")
    result = DungeonRuntimePathHistoryAuditor().audit_state_dict(data)
    assert result.ok is True
    assert result.status == "WARN"
    assert result.current_equals_last_history is True
    assert any(c.name == "current_not_last_history" and c.status == "WARN" for c in result.checks)


def test_audit_detects_ping_pong_pattern_like_tenebrous_smoke():
    data = {
        "campaign_id": "tenebrous",
        "current": pos("tenebrous:L01:HV0001", segment_id="tenebrous:L01:HV0001"),
        "path_history": [
            pos("tenebrous:L01:R061", "room", room_id="tenebrous:L01:R061", segment_id=None, cell=None),
            pos("tenebrous:L01:HV0950", segment_id="tenebrous:L01:HV0950"),
            pos("tenebrous:L01:HV0001", segment_id="tenebrous:L01:HV0001"),
            pos("tenebrous:L01:HV0950", segment_id="tenebrous:L01:HV0950"),
            pos("tenebrous:L01:HV0001", segment_id="tenebrous:L01:HV0001"),
            pos("tenebrous:L01:HV0950", segment_id="tenebrous:L01:HV0950"),
        ],
    }
    result = DungeonRuntimePathHistoryAuditor().audit_state_dict(data)
    assert result.ok is True
    assert result.status == "WARN"
    assert result.ping_pong_pair_count >= 2
    assert result.unique_positions == 3
    assert any(c.name == "ping_pong_pattern" and c.status == "WARN" for c in result.checks)


def test_audit_invalid_entries_fail():
    data = clean_state()
    data["path_history"].append({"bad": "entry"})
    result = DungeonRuntimePathHistoryAuditor().audit_state_dict(data)
    assert result.ok is False
    assert result.status == "FAIL"
    assert result.invalid_entries == 1


def test_audit_file_roundtrip(tmp_path: Path):
    p = tmp_path / "visibility_runtime_state_ch.json"
    p.write_text(json.dumps(clean_state(), ensure_ascii=False), encoding="utf-8")
    result = DungeonRuntimePathHistoryAuditor().audit_file(p)
    assert result.ok is True
    assert result.state_file == str(p)
