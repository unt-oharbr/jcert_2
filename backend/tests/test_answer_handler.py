"""Tests for lambdas/answer/handler.py's T2 tier-demotion-suspension wiring
and T3's same-question retry.

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

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        # Only ever called by the handler as `SET attempts = :a` — a real
        # expression parser would be overkill for a test double, so this
        # just applies the one attribute the handler actually sets.
        assert UpdateExpression == "SET attempts = :a"
        self.item = {**(self.item or {}), "attempts": ExpressionAttributeValues[":a"]}


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


def _question_item(*, question_id: str = "q1", answer_type: str = "value", answer: str = "7", attempts: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "questionId": question_id,
        "userId": "user-123",
        "topicId": "algebra_equations",
        "subtopic": "simplifying_expressions",
        "difficulty": "intro",
        "answerType": answer_type,
        "answer": answer,
        "commonWrongAnswers": [],
    }
    if attempts is not None:
        item["attempts"] = attempts
    return item


def _submit(
    handler_module, *, questions_table, progress_item, streaks_item, correct: bool, submitted_answer: str | None = None
):
    """Answer one question against the given prior progress/streak state.

    `correct`/`submitted_answer` are mutually exclusive shorthands: pass
    `correct` for the default "7"-answer question, or `submitted_answer` to
    submit a specific string (e.g. a specific wrong inequality direction)
    against whatever question `questions_table` holds.
    """
    handler_module._questions_table = questions_table
    handler_module._progress_table = _FakeTable(item=progress_item)
    handler_module._streaks_table = _FakeTable(item=streaks_item)
    handler_module._attempts_table = _FakeTable()

    answer = submitted_answer if submitted_answer is not None else ("7" if correct else "wrong-answer")
    response = handler_module.handler(_event("q1", answer), None)
    body = json.loads(response["body"])
    return body, handler_module._progress_table.item, handler_module._streaks_table.item


def _questions_table_for(question_item):
    return _FakeTable(item=question_item)


def test_wrong_answer_at_question_12_does_not_demote(handler_module):
    # Already 11 questions answered today (this submission will be the 12th),
    # and one prior miss this tier (this wrong answer would be the demoting
    # second miss under normal rules). attempts=1: a resolving (not a
    # retry-offering) wrong answer — see the T3 section below for the retry
    # path itself; this test is purely about T2's demotion suspension.
    streaks_item = {
        "userId": "user-123",
        "currentDailyStreak": 1,
        "questionsToday": 11,
        "questionsTodayDate": _TODAY_ISO,
    }
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 1}

    body, new_progress, new_streaks = _submit(
        handler_module,
        questions_table=_questions_table_for(_question_item(attempts=1)),
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
        questions_table=_questions_table_for(_question_item(attempts=1)),
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


# --- T3: same-question retry before the worked example ---


def test_wrong_first_attempt_offers_a_retry_without_revealing_anything(handler_module):
    questions_table = _questions_table_for(_question_item())
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 2, "tierMisses": 0}
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, new_progress, new_streaks = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=False,
    )

    assert body["secondAttemptAvailable"] is True
    assert body["correctAnswer"] is None
    assert body["diagnosticOffer"] is None
    assert body["progress"]["tier"] == "standard"  # unchanged, not yet resolved
    assert questions_table.item["attempts"] == 1
    # Nothing was finalized yet: neither table got a fresh write reflecting
    # this attempt (both still hold exactly what was there before).
    assert new_progress is progress_item
    assert new_streaks is streaks_item


def test_wrong_twice_resolves_as_a_single_miss(handler_module):
    # Already one miss this tier — a second, undifferentiated miss would
    # normally demote. This is that second miss (a first-attempt miss
    # already happened and offered the retry; this is the follow-up wrong
    # answer on the same question), and it should demote exactly once, not
    # be double-counted for having taken two attempts to arrive at.
    questions_table = _questions_table_for(_question_item(attempts=1))
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 1}
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, new_progress, _ = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=False,
    )

    assert body["secondAttemptAvailable"] is False
    assert body["diagnosticOffer"] is not None
    assert body["progress"]["tier"] == "intro"  # demoted — exactly the same as any single second miss
    assert new_progress["tier"] == "intro"


def test_second_attempt_correct_does_not_advance_the_tier(handler_module):
    # tierStreak=2 is one correct answer away from advancing (3-in-a-row).
    # If this second-attempt correct counted normally, it would advance.
    questions_table = _questions_table_for(_question_item(attempts=1))
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 2, "tierMisses": 0}
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, new_progress, _ = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=True,
    )

    assert body["correct"] is True
    assert body["progress"]["tier"] == "standard"  # not advanced
    assert new_progress["tierStreak"] == 2  # unchanged, not reset and not incremented


def test_second_attempt_correct_does_not_earn_a_badge_it_would_have_on_a_first_attempt(handler_module):
    # streak=4 -> a first-attempt correct would hit 5 and qualify for the
    # intro badge (standard/full tier, streak>=5). Neutral means it doesn't.
    questions_table = _questions_table_for(_question_item(attempts=1))
    progress_item = {
        "userId": "user-123",
        "topicId": "algebra_equations",
        "tier": "standard",
        "tierStreak": 4,
        "tierMisses": 0,
        "introBadgeEarned": False,
    }
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, _, _ = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=True,
    )

    assert body["progress"]["introBadgeEarned"] is False


def test_first_attempt_correct_still_advances_normally(handler_module):
    # Sanity check: T3 shouldn't change first-attempt-correct behaviour.
    questions_table = _questions_table_for(_question_item())
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 2, "tierMisses": 0}
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, _, _ = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=True,
    )

    assert body["progress"]["tier"] == "full"  # 3rd in a row, advances


def test_inequality_subtopic_skips_the_retry_and_resolves_immediately(handler_module):
    questions_table = _questions_table_for(_question_item(answer_type="inequality", answer="x > 3"))
    progress_item = {"userId": "user-123", "topicId": "algebra_equations", "tier": "standard", "tierStreak": 0, "tierMisses": 0}
    streaks_item = {"userId": "user-123", "currentDailyStreak": 1, "questionsToday": 3, "questionsTodayDate": _TODAY_ISO}

    body, new_progress, _ = _submit(
        handler_module,
        questions_table=questions_table,
        progress_item=progress_item,
        streaks_item=streaks_item,
        correct=False,
        submitted_answer="x < 3",  # wrong direction, first and only attempt
    )

    assert body["secondAttemptAvailable"] is False
    assert body["correctAnswer"] == "x > 3"  # resolved immediately, answer is revealed
    assert body["diagnosticOffer"] is not None
    assert new_progress["tierMisses"] == 1  # counted as a normal miss, no retry offered
    assert "attempts" not in questions_table.item  # never entered the retry path
