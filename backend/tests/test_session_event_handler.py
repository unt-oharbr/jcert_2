"""Tests for lambdas/session_event/handler.py — T4's frontend-lifecycle event sink.

Same load-by-file-path-and-fake-tables approach as
test_next_question_handler.py — see that file's docstring for why.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_HANDLER_PATH = Path(__file__).parent.parent / "lambdas" / "session_event" / "handler.py"


class _FakeTable:
    def __init__(self, *, raise_on_put: bool = False):
        self.raise_on_put = raise_on_put
        self.put_items: list[dict[str, Any]] = []

    def put_item(self, Item):
        if self.raise_on_put:
            raise RuntimeError("simulated DynamoDB failure")
        self.put_items.append(Item)


def _event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user-123"}}}},
        "body": json.dumps(body),
    }


@pytest.fixture
def handler_module(monkeypatch):
    monkeypatch.setenv("SESSION_EVENTS_TABLE", "test-session-events")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

    spec = importlib.util.spec_from_file_location("session_event_handler_under_test", _HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules.pop(spec.name, None)
    return module


def test_logs_a_recognised_frontend_event(handler_module):
    table = _FakeTable()
    handler_module._table = table

    response = handler_module.handler(_event({"eventType": "session_start", "sessionId": "sess-1"}), None)

    assert response["statusCode"] == 200
    assert len(table.put_items) == 1
    assert table.put_items[0]["eventType"] == "session_start"
    assert table.put_items[0]["sessionId"] == "sess-1"
    assert table.put_items[0]["userId"] == "user-123"


def test_extra_body_fields_become_the_event_data(handler_module):
    table = _FakeTable()
    handler_module._table = table

    handler_module.handler(
        _event({"eventType": "block_complete", "sessionId": "sess-1", "questionsToday": 5}), None
    )

    assert table.put_items[0]["data"] == {"questionsToday": 5}


@pytest.mark.parametrize("event_type", ["question_shown", "answer_submitted", "tier_change", "made_up_event", None])
def test_non_frontend_event_types_are_rejected(handler_module, event_type):
    # question_shown/answer_submitted/tier_change are logged server-side by
    # next_question/answer directly, not accepted from the client here.
    table = _FakeTable()
    handler_module._table = table

    response = handler_module.handler(_event({"eventType": event_type, "sessionId": "sess-1"}), None)

    assert response["statusCode"] == 400
    assert table.put_items == []


def test_a_write_failure_never_surfaces_as_an_unhandled_error(handler_module):
    handler_module._table = _FakeTable(raise_on_put=True)

    response = handler_module.handler(_event({"eventType": "session_start", "sessionId": "sess-1"}), None)

    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["logged"] is False
