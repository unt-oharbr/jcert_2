"""Tests for lambdas/next_question/handler.py's failure handling (T1).

Loaded by file path rather than via a package import: the handler is deployed
and invoked as a top-level `handler` module (see backend_stack.py's
handler="handler.handler"), and every lambdas/*/handler.py shares that same
module name, so importing by spec avoids collisions with any other handler's
tests in the same pytest run.

DynamoDB access is faked with small hand-written stand-ins rather than a
mocking library — consistent with the rest of this suite, which has no
mocking dependency at all.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, ClassVar

import pytest

_HANDLER_PATH = Path(__file__).parent.parent / "lambdas" / "next_question" / "handler.py"


class _FakeTable:
    def __init__(self, *, item: dict[str, Any] | None = None, raise_on_put: bool = False):
        self.item = item
        self.raise_on_put = raise_on_put
        self.put_items: list[dict[str, Any]] = []

    def get_item(self, Key):  # matches boto3's Table.get_item(Key=...) signature
        return {"Item": self.item} if self.item is not None else {}

    def put_item(self, Item):  # matches boto3's Table.put_item(Item=...) signature
        if self.raise_on_put:
            raise RuntimeError("simulated DynamoDB failure")
        self.put_items.append(Item)


class _FakeTopic:
    """A stand-in topic module with a `generate` that always raises."""

    TOPIC_LABEL = "Fake Topic"
    SUBTOPICS: ClassVar[list[str]] = ["fake_subtopic"]

    @staticmethod
    def generate(subtopic, tier, rng):
        raise RuntimeError("simulated generation failure")


def _event(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user-123"}}}},
        "body": json.dumps(body or {}),
    }


@pytest.fixture
def handler_module(monkeypatch):
    monkeypatch.setenv("QUESTIONS_TABLE", "test-questions")
    monkeypatch.setenv("PROGRESS_TABLE", "test-progress")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

    spec = importlib.util.spec_from_file_location("next_question_handler_under_test", _HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules.pop(spec.name, None)  # don't leak into later tests' import caches
    return module


def test_generation_failure_returns_structured_retryable_response_not_a_raise(handler_module, caplog):
    handler_module._questions_table = _FakeTable()
    handler_module._progress_table = _FakeTable()
    handler_module.TOPICS = {"fake_topic": _FakeTopic}

    with caplog.at_level(logging.ERROR):
        response = handler_module.handler(_event({"topicId": "fake_topic", "subtopic": "fake_subtopic"}), None)

    assert response["statusCode"] != 200
    body = json.loads(response["body"])
    assert "questionId" not in body  # distinguishable from a success payload
    assert body["retryable"] is True


def test_generation_failure_logs_topic_subtopic_and_tier(handler_module, caplog):
    handler_module._questions_table = _FakeTable()
    handler_module._progress_table = _FakeTable(item={"tier": "standard"})
    handler_module.TOPICS = {"fake_topic": _FakeTopic}

    with caplog.at_level(logging.ERROR):
        handler_module.handler(_event({"topicId": "fake_topic", "subtopic": "fake_subtopic"}), None)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "fake_topic" in message
    assert "fake_subtopic" in message
    assert "standard" in message


def test_persistence_failure_after_successful_generation_is_also_recovered(handler_module, caplog):
    handler_module._questions_table = _FakeTable(raise_on_put=True)
    handler_module._progress_table = _FakeTable()
    # Real generator here (not _FakeTopic): proves a failure *after*
    # generation succeeds (the DynamoDB write) is caught too, not just a
    # generation-time exception.

    with caplog.at_level(logging.ERROR):
        response = handler_module.handler(_event({}), None)

    assert response["statusCode"] != 200
    assert len(caplog.records) == 1


def test_happy_path_is_unaffected(handler_module):
    questions_table = _FakeTable()
    handler_module._questions_table = questions_table
    handler_module._progress_table = _FakeTable()

    response = handler_module.handler(_event({}), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["questionId"]
    assert body["prompt"]
    assert len(questions_table.put_items) == 1
