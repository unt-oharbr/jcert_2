from scripts.session_report import _format_timeline, _most_recent_session_events


def _event(event_type: str, *, timestamp: str, session_id: str = "sess-1", data: dict | None = None) -> dict:
    return {
        "userId": "user-123",
        "eventId": f"{timestamp}#abc",
        "timestamp": timestamp,
        "eventType": event_type,
        "sessionId": session_id,
        "data": data or {},
    }


def test_most_recent_session_events_groups_by_the_latest_session_start():
    # Two sessions in the fetched (newest-first) page — only the second's
    # events should come back, in chronological (oldest-first) order.
    events_newest_first = [
        _event("session_end", timestamp="t4", session_id="sess-2"),
        _event("question_shown", timestamp="t3", session_id="sess-2"),
        _event("session_start", timestamp="t2", session_id="sess-2"),
        _event("session_end", timestamp="t1", session_id="sess-1"),
        _event("session_start", timestamp="t0", session_id="sess-1"),
    ]

    session_id, events = _most_recent_session_events(events_newest_first)

    assert session_id == "sess-2"
    assert [e["timestamp"] for e in events] == ["t2", "t3", "t4"]


def test_most_recent_session_events_falls_back_when_no_session_start_found():
    events_newest_first = [
        _event("answer_submitted", timestamp="t2"),
        _event("question_shown", timestamp="t1"),
    ]

    session_id, events = _most_recent_session_events(events_newest_first)

    assert session_id is None
    assert [e["timestamp"] for e in events] == ["t1", "t2"]  # oldest first


def test_format_timeline_reports_a_question_with_two_attempts():
    events = [
        _event("session_start", timestamp="t0"),
        _event(
            "question_shown",
            timestamp="t1",
            data={"questionId": "q1", "subtopic": "inequalities", "tier": "standard"},
        ),
        _event(
            "answer_submitted",
            timestamp="t2",
            data={"questionId": "q1", "attemptNumber": 1, "correct": False, "millisecondsSinceShown": 4000},
        ),
        _event(
            "answer_submitted",
            timestamp="t3",
            data={"questionId": "q1", "attemptNumber": 2, "correct": True, "millisecondsSinceShown": 9000},
        ),
        _event("session_end", timestamp="t4"),
    ]

    timeline = _format_timeline(events)

    assert "inequalities" in timeline
    assert "tier=standard" in timeline
    assert "2 attempt(s)" in timeline
    assert "correct" in timeline
    assert "9000ms" in timeline
    assert "Session ended" in timeline
    assert "abandoned" not in timeline


def test_format_timeline_flags_an_absent_session_end_without_erroring():
    events = [_event("session_start", timestamp="t0")]

    timeline = _format_timeline(events)

    assert "no session_end recorded" in timeline
