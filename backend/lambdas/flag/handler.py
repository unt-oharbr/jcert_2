"""POST /questions/{questionId}/flag — she can flag a question as wrong,
confusing, already seen, or too hard, with an optional note.

Persists everything needed to reproduce the exact question later: topic,
subtopic, tier, and the RNG seed next_question/handler.py generated it
with — re-running `topic.generate(subtopic, tier, random.Random(seed))`
reproduces the identical prompt/answer, since the generators are pure
functions of those inputs (see scripts/list_flags.py, which actually does
this rather than just printing the raw numbers).

No confirmation step, no modal: a flag is submitted the instant she taps a
reason, and this handler's only job is to persist it and say so — nothing
here should ever interrupt the question she's already looking at.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import boto3

_questions_table = boto3.resource("dynamodb").Table(os.environ["QUESTIONS_TABLE"])
_flags_table = boto3.resource("dynamodb").Table(os.environ["FLAGS_TABLE"])

# One tap, one of these four — see docs/spec.md-adjacent brief. A closed
# set for the same reason axiom.events.EVENT_TYPES and
# docs/misconceptions.md's fix are closed: an uncontrolled reason string
# would fragment silently instead of failing loudly.
REASONS = frozenset({"wrong_answer", "confusing", "seen_before", "too_hard"})


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)
    question_id = event["pathParameters"]["questionId"]
    body = json.loads(event.get("body") or "{}")
    reason = body.get("reason")
    note = body.get("note", "")
    submitted_answer = body.get("submittedAnswer", "")

    if reason not in REASONS:
        return _response(400, {"error": f"Unknown reason '{reason}'. Expected one of {sorted(REASONS)}."})

    question_item = _questions_table.get_item(Key={"questionId": question_id}).get("Item")
    if question_item is None:
        return _response(404, {"error": "That question wasn't found — it may have expired."})
    if question_item.get("userId") != user_id:
        return _response(403, {"error": "That's not your question."})

    _flags_table.put_item(
        Item={
            "questionId": question_id,
            "userId": user_id,
            "topicId": question_item["topicId"],
            "subtopic": question_item["subtopic"],
            "difficulty": question_item["difficulty"],
            # Both stored: `seed` is what actually reproduces the question
            # (see module docstring); `prompt` lets a human read the flag
            # without re-running anything. Older questions served before
            # T7 landed won't have a seed — .get() rather than [] so those
            # can still be flagged, just without exact reproducibility.
            "seed": question_item.get("seed"),
            "prompt": question_item.get("prompt"),
            "canonicalAnswer": question_item["answer"],
            "submittedAnswer": submitted_answer,
            "reason": reason,
            "note": note,
            "timestamp": str(time.time()),
        }
    )

    return _response(200, {"flagged": True})
