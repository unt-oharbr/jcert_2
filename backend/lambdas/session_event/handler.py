"""POST /session/event — invisible instrumentation (T4).

Frontend-only lifecycle events that have no natural backend touchpoint:
session_start, session_end, worked_example_shown, worked_example_dismissed,
block_complete. Grading-pipeline events (question_shown, answer_submitted,
tier_change) are logged inline in next_question/answer instead, since those
handlers already hold the authoritative data — see axiom/events.py.

Fire-and-forget from the frontend: this endpoint never needs to surface a
failure to her, so a write failure here is swallowed rather than returned
as a 5xx — there's nothing for the client to recover from either way, and
an unhandled exception would just be noise in the logs for a table nothing
else depends on.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

from axiom.events import build_event_item

_table = boto3.resource("dynamodb").Table(os.environ["SESSION_EVENTS_TABLE"])

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

# Only the events with no backend touchpoint of their own — see module
# docstring. question_shown/answer_submitted/tier_change are logged by
# next_question/answer directly and are deliberately not accepted here.
_FRONTEND_EVENT_TYPES = frozenset(
    {"session_start", "session_end", "worked_example_shown", "worked_example_dismissed", "block_complete"}
)


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)
    body = json.loads(event.get("body") or "{}")
    event_type = body.get("eventType")
    session_id = body.get("sessionId")
    data = {k: v for k, v in body.items() if k not in {"eventType", "sessionId"}}

    if event_type not in _FRONTEND_EVENT_TYPES:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"logged": False}),
        }

    try:
        item = build_event_item(user_id=user_id, session_id=session_id, event_type=event_type, data=data)
        _table.put_item(Item=item)
    except Exception:
        _logger.exception("Failed to log %s event (non-fatal, fire-and-forget)", event_type)
        return {
            "statusCode": 202,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"logged": False}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"logged": True, "eventId": item["eventId"]}),
    }
