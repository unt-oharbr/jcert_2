from axiom.events import EVENT_TYPES, build_event_item


def test_build_event_item_has_all_expected_fields():
    item = build_event_item(user_id="user-123", session_id="sess-1", event_type="session_start", data={"foo": "bar"})
    assert item["userId"] == "user-123"
    assert item["sessionId"] == "sess-1"
    assert item["eventType"] == "session_start"
    assert item["data"] == {"foo": "bar"}
    assert item["timestamp"] in item["eventId"]  # sort key is timestamp-prefixed


def test_unknown_event_type_is_rejected():
    try:
        build_event_item(user_id="user-123", session_id=None, event_type="made_up_event", data={})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_every_declared_event_type_is_accepted():
    for event_type in EVENT_TYPES:
        item = build_event_item(user_id="user-123", session_id=None, event_type=event_type, data={})
        assert item["eventType"] == event_type


def test_session_id_is_optional():
    item = build_event_item(user_id="user-123", session_id=None, event_type="session_start", data={})
    assert item["sessionId"] is None


def test_successive_event_timestamps_do_not_go_backwards():
    first = build_event_item(user_id="user-123", session_id=None, event_type="session_start", data={})
    second = build_event_item(user_id="user-123", session_id=None, event_type="session_end", data={})
    assert first["timestamp"] <= second["timestamp"]
