"""Session event log — invisible instrumentation, never read by the frontend.

The only record of a session besides over-the-shoulder observation. Each row
is one event in a user's practice history: partition key `userId`, sort key
an ISO 8601 timestamp plus a short random tie-breaker — not a true atomic
sequence counter, which would need a separate counter item to stay correct
under concurrent writes. These are one-client, one-event-at-a-time writes
for a single user, so a random tie-breaker is enough to keep the sort key
unique; the timestamp prefix alone already gives correct chronological
ordering except for events landing in the exact same millisecond, which
don't need a strict relative order beyond "roughly simultaneous."
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

EVENT_TYPES = frozenset(
    {
        "session_start",
        "question_shown",
        "answer_submitted",
        "worked_example_shown",
        "worked_example_dismissed",
        "tier_change",
        "block_complete",
        "session_end",
    }
)


def build_event_item(*, user_id: str, session_id: str | None, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """An event row ready for `put_item`. Raises ValueError for an unknown
    `event_type` — the event taxonomy is closed, same reasoning as
    docs/misconceptions.md's closed-taxonomy fix: an uncontrolled string here
    would fragment silently instead of failing loudly."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type '{event_type}'. Expected one of {sorted(EVENT_TYPES)}.")

    timestamp = datetime.now(UTC).isoformat()
    event_id = f"{timestamp}#{uuid.uuid4().hex[:6]}"
    return {
        "userId": user_id,
        "eventId": event_id,
        "timestamp": timestamp,
        "eventType": event_type,
        "sessionId": session_id,
        "data": data,
    }
