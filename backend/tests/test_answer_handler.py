"""Tests for lambdas/answer/handler.py's T2 tier-demotion-suspension wiring.

Same load-by-file-path-and-fake-tables approach as
test_next_question_handler.py — see that file's docstring for why.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

_HANDLER_PATH = Path(__file__).parent.parent / "lambdas" / "answer" / "handler.py"
_TODAY_ISO = datetime.now(UTC).date().isoformat()


class _FakeTable:
    def __init__(self, *, item: dict[str, Any] | None = None):
        self.item = item
        self.put_items: list[dict[str, Any]] = []

    def get_item(self, Key):  # matches boto3's Table.get_item(Key=...) signature
        return {"Item": self.item} if self.item is not None else {}

    def put_item(self, Item):  # matches boto3's Table.put_item(Item=...) signature
        self.item = Item  # so a second call in the same test sees the latest state
        self.put_items.append(Item)


def _event(question_id: str, answer: str) -> dict[str, Any]:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user-123"}}}},
        "body": json.dumps({"questionId": question_id, "answer": answer}),
    }


@pytest.fixture
def handler_module(monkeypatch):
    for var in ("QUESTIONS_TABLE", "ATTEMPTS_TABLE", "PROGRESS_TABLE", "STREAKS_TABLE"):
        monkeypatch.setenv(var, f"test-{var.lower()}")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

    spec = importlib.util.spec_from_file_location("answer_handler_under_test", _HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules.pop(spec.name, None)
    return module


def _question_item(*, question_id: str = "q1") -> dict[str, Any]:
    return {
        "questionId": question_id,
        "userId": "user-123",
        "topicId": "algebra_equations",
        "subtopic": "simplifying_expressions",
        "difficulty": "intro",
        "answerType": "value",
        "answer": "7",
        "commonWrongAnswers": [],
    }


def _submit(handler_module, *, questions_table, progress_item, streaks_item, correct: bool):
    """Answer one question, wrong or right, against the given prior progress/streak state."""
    handler_module._questions_table = questions_table
    handler_module._progress_table = _FakeTable(item=progress_item)
    handler_module._streaks_table = _FakeTable(item=streaks_item)
    handler_module._attempts_table = _FakeTable()

    answer = "7" if correct else "wrong-answer"
    response = handler_module.handler(_event("q1", answer), None)
    body = json.loads(response["body"])
    return body, handler_module._progress_table.item, handler_module._streaks_table.item


def _questions_table_for(question_item):
    return _FakeTable(item=question_item)


def test_wrong_answer_at_question_12_does_not_demote(handler_module):
    # Already 11 questions answered today (this submission will be the 12th),
    # and one prior miss this tier (this wrong answer would be the demoting
    # second miss under normal rules).
    streaks_item = {
        "userId": "user-123",
        "currentDailyStreak": 1,
        "questionsToday": 11,
        "questionsTodayDate": _TODAY_ISO,
    }
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 1}

    body, new_progress, new_streaks = _submit(
        handler_module,
        questions_table=_questions_table_for(_question_item()),
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=False,
    )

    assert body["correct"] is False
    assert body["progress"]["tier"] == "standard"  # not demoted
    assert new_progress["tier"] == "standard"
    assert new_streaks["questionsToday"] == 12


def test_three_right_starting_at_question_12_still_advances(handler_module):
    streaks_item = {
        "userId": "user-123",
        "currentDailyStreak": 1,
        "questionsToday": 11,
        "questionsTodayDate": _TODAY_ISO,
    }
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 0}

    for _ in range(3):
        body, progress_item, streaks_item = _submit(
            handler_module,
            questions_table=_questions_table_for(_question_item()),
            progress_item=progress_item,
            streaks_item=streaks_item,
            correct=True,
        )
        assert body["questionsToday"] > 10  # confirms this really ran with suspension active throughout

    assert body["progress"]["tier"] == "full"


def test_demotion_applies_normally_before_question_11(handler_module):
    streaks_item = {
        "userId": "user-123",
        "currentDailyStreak": 1,
        "questionsToday": 3,
        "questionsTodayDate": _TODAY_ISO,
    }
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 1}

    body, _, _ = _submit(
        handler_module,
        questions_table=_questions_table_for(_question_item()),
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=False,
    )

    assert body["progress"]["tier"] == "intro"  # second miss, demoted as normal


def test_response_reports_questions_today(handler_module):
    body, _, _ = _submit(
        handler_module,
        questions_table=_questions_table_for(_question_item()),
        progress_item=None,
        streaks_item=None,
        correct=True,
    )

    assert body["questionsToday"] == 1
