"""POST /session/next-question — generate and serve a fresh question instance
at her current difficulty tier.

Picks a random topic/subtopic by default. After a wrong answer, the client
instead asks for another instance of the *same* subtopic (optional
`topicId`/`subtopic` in the request body) — a slip or a gap both deserve a
similar question to actually retry, not a random new one that proves
nothing either way.

Generation and persistence are wrapped so a failure here never reaches the
client as a bare 5xx with no way forward — see docs/home-view.md's "never a
dead end" constraint. The failure is logged with enough to reproduce it
(topic/subtopic/tier — the inputs to generation) and the client gets a
structured, retryable response instead of an unhandled exception.

Also logs a `question_shown` event (T4's session log) once the question is
successfully generated — in its own try/except, separate from the
generation one above, so a SessionEvents write failure can never turn a
perfectly good question into a failed response.

Every question is generated from an explicit random seed (stored alongside
it) rather than an unseeded `random.Random()` — this is what makes T7's
flagged questions exactly reproducible later: `topic.generate(subtopic,
tier, random.Random(seed))` deterministically recreates the identical
prompt/answer, since the generators are pure functions of their inputs.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid
from typing import Any

import boto3

from axiom.events import build_event_item
from axiom.topics import TOPICS

_SERVED_TTL_SECONDS = 60 * 60 * 24  # a day is more than enough to answer or abandon a question

_questions_table = boto3.resource("dynamodb").Table(os.environ["QUESTIONS_TABLE"])
_progress_table = boto3.resource("dynamodb").Table(os.environ["PROGRESS_TABLE"])
_session_events_table = boto3.resource("dynamodb").Table(os.environ["SESSION_EVENTS_TABLE"])

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _current_tier(user_id: str, topic_id: str) -> str:
    item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item")
    return item.get("tier", "intro") if item else "intro"


def _generation_failed_response() -> dict[str, Any]:
    # Deliberately no "error"/"failed"/"sorry" wording here isn't required —
    # this body is never rendered as-is; the frontend owns the copy shown to
    # her. This shape just needs to be reliably distinguishable from a
    # successful question payload (no questionId/prompt) so the client
    # doesn't have to guess from status code alone.
    return {
        "statusCode": 503,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "unavailable", "retryable": True}),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)
    body = json.loads(event.get("body") or "{}")
    requested_topic_id = body.get("topicId")
    requested_subtopic = body.get("subtopic")
    session_id = body.get("sessionId")

    if requested_topic_id in TOPICS and requested_subtopic in TOPICS[requested_topic_id].SUBTOPICS:
        topic_id, topic = requested_topic_id, TOPICS[requested_topic_id]
        subtopic = requested_subtopic
    else:
        topic_id, topic = random.choice(list(TOPICS.items()))
        subtopic = random.choice(topic.SUBTOPICS)

    tier = "unknown"  # overwritten below; kept so a failed _current_tier call still logs something
    try:
        tier = _current_tier(user_id, topic_id)
        seed = random.randrange(2**32)
        question = topic.generate(subtopic, tier, random.Random(seed))

        question_id = str(uuid.uuid4())
        _questions_table.put_item(
            Item={
                "questionId": question_id,
                "userId": user_id,
                "topicId": topic_id,
                "subtopic": question.subtopic,
                "difficulty": question.difficulty,
                "answerType": question.answer_type,
                "answer": question.answer,
                "commonWrongAnswers": question.common_wrong_answers,
                "prompt": question.prompt,
                "seed": seed,
                "ttl": int(time.time()) + _SERVED_TTL_SECONDS,
            }
        )
    except Exception:
        # Logged, not re-raised: an unhandled exception here would reach the
        # client as a bare 5xx with no way forward. topic_id/subtopic/tier are
        # exactly the inputs needed to attempt a same-inputs retry — a failure
        # here happens before `seed` exists, so an exact repro of the specific
        # failed attempt still isn't possible, only of questions that make it
        # past this point (see the `seed` field stored above).
        _logger.exception(
            "next_question failed to generate/persist a question (topicId=%s, subtopic=%s, tier=%s)",
            topic_id,
            subtopic,
            tier,
        )
        return _generation_failed_response()

    try:
        _session_events_table.put_item(
            Item=build_event_item(
                user_id=user_id,
                session_id=session_id,
                event_type="question_shown",
                data={
                    "questionId": question_id,
                    "topicId": topic_id,
                    "subtopic": question.subtopic,
                    "tier": question.difficulty,
                    "prompt": question.prompt,
                },
            )
        )
    except Exception:
        # Non-fatal: the question was generated and served fine either way —
        # see this module's docstring.
        _logger.exception("Failed to log question_shown event (non-fatal)")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "questionId": question_id,
                "topicId": topic_id,
                "topicLabel": topic.TOPIC_LABEL,
                "subtopic": question.subtopic,
                "difficulty": question.difficulty,
                "type": question.type,
                "answerType": question.answer_type,
                "prompt": question.prompt,
                # Not every topic's Question has this attribute (only the
                # coordinate-geometry generators produce one) — getattr
                # keeps this handler from needing to know which topics do.
                "visualization": getattr(question, "visualization", None),
            }
        ),
    }
