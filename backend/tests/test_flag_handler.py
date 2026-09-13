"""Tests for lambdas/flag/handler.py — T7's real flag logic.

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

_HANDLER_PATH = Path(__file__).parent.parent / "lambdas" / "flag" / "handler.py"


class _FakeTable:
    def __init__(self, *, item: dict[str, Any] | None = None):
        self.item = item
        self.put_items: list[dict[str, Any]] = []

    def get_item(self, Key):  # matches boto3's Table.get_item(Key=...) signature
        return {"Item": self.item} if self.item is not None else {}

    def put_item(self, Item):  # matches boto3's Table.put_item(Item=...) signature
        self.put_items.append(Item)


def _event(question_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user-123"}}}},
        "pathParameters": {"questionId": question_id},
        "body": json.dumps(body),
    }


@pytest.fixture
def handler_module(monkeypatch):
    monkeypatch.setenv("QUESTIONS_TABLE", "test-questions")
    monkeypatch.setenv("FLAGS_TABLE", "test-flags")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

    spec = importlib.util.spec_from_file_location("flag_handler_under_test", _HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules.pop(spec.name, None)
    return module


def _question_item() -> dict[str, Any]:
    return {
        "questionId": "q1",
        "userId": "user-123",
        "topicId": "algebra_equations",
        "subtopic": "solving_linear_equations",
        "difficulty": "standard",
        "answerType": "value",
        "answer": "7",
        "seed": 12345,
        "prompt": "Solve for x: 3x + 2 = 23",
    }


def test_a_valid_flag_is_persisted_with_everything_needed_to_reproduce_it(handler_module):
    handler_module._questions_table = _FakeTable(item=_question_item())
    flags_table = _FakeTable()
    handler_module._flags_table = flags_table

    response = handler_module.handler(
        _event("q1", {"reason": "too_hard", "note": "needs a hint", "submittedAnswer": "12"}), None
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"flagged": True}
    assert len(flags_table.put_items) == 1
    flag = flags_table.put_items[0]
    assert flag["reason"] == "too_hard"
    assert flag["note"] == "needs a hint"
    assert flag["submittedAnswer"] == "12"
    assert flag["seed"] == 12345
    assert flag["prompt"] == "Solve for x: 3x + 2 = 23"
    assert flag["canonicalAnswer"] == "7"
    assert flag["topicId"] == "algebra_equations"
    assert flag["subtopic"] == "solving_linear_equations"
    assert flag["difficulty"] == "standard"


def test_note_is_optional(handler_module):
    handler_module._questions_table = _FakeTable(item=_question_item())
    flags_table = _FakeTable()
    handler_module._flags_table = flags_table

    response = handler_module.handler(_event("q1", {"reason": "confusing"}), None)

    assert response["statusCode"] == 200
    assert flags_table.put_items[0]["note"] == ""


@pytest.mark.parametrize("reason", ["not_a_real_reason", None, "", "wrong-answer"])
def test_an_unrecognised_reason_is_rejected(handler_module, reason):
    handler_module._questions_table = _FakeTable(item=_question_item())
    handler_module._flags_table = _FakeTable()

    response = handler_module.handler(_event("q1", {"reason": reason}), None)

    assert response["statusCode"] == 400
    assert handler_module._flags_table.put_items == []


def test_flagging_a_question_that_does_not_exist_is_a_404(handler_module):
    handler_module._questions_table = _FakeTable(item=None)
    handler_module._flags_table = _FakeTable()

    response = handler_module.handler(_event("nonexistent", {"reason": "too_hard"}), None)

    assert response["statusCode"] == 404


def test_flagging_someone_elses_question_is_a_403(handler_module):
    other_users_question = {**_question_item(), "userId": "someone-else"}
    handler_module._questions_table = _FakeTable(item=other_users_question)
    handler_module._flags_table = _FakeTable()

    response = handler_module.handler(_event("q1", {"reason": "too_hard"}), None)

    assert response["statusCode"] == 403


def test_a_question_served_before_t7_can_still_be_flagged_without_a_seed(handler_module):
    pre_t7_question = {k: v for k, v in _question_item().items() if k not in {"seed", "prompt"}}
    handler_module._questions_table = _FakeTable(item=pre_t7_question)
    flags_table = _FakeTable()
    handler_module._flags_table = flags_table

    response = handler_module.handler(_event("q1", {"reason": "seen_before"}), None)

    assert response["statusCode"] == 200
    assert flags_table.put_items[0]["seed"] is None
