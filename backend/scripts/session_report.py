"""Print the most recent practice session as a readable timeline.

The only record of a session besides over-the-shoulder observation (T4) —
this is the terminal-only substitute for an admin console that doesn't
exist yet. Reads AxiomSessionEvents directly; nothing here is read by the
app itself.

A "session" is everything sharing the most recent session_start event's
sessionId. If no session_end shows up in that group, the session is
reported as still open/abandoned rather than assumed complete — closing
the tab or losing network never reliably fires a clean exit, so its
absence has to be a normal, readable outcome, not an error.

Usage:
    uv run python scripts/session_report.py --user-id <cognito-sub>
"""

from __future__ import annotations

import argparse
from typing import Any

import boto3

_RECENT_EVENTS_LIMIT = 500


def _fetch_recent_events(*, table_name: str, region: str, user_id: str) -> list[dict[str, Any]]:
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    response = table.query(
        KeyConditionExpression="userId = :u",
        ExpressionAttributeValues={":u": user_id},
        ScanIndexForward=False,  # newest first
        Limit=_RECENT_EVENTS_LIMIT,
    )
    return response.get("Items", [])


def _most_recent_session_events(events_newest_first: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """The events belonging to the most recent session_start's sessionId, oldest first.

    Falls back to everything fetched (still oldest-first) if no
    session_start turns up in the fetched page at all — better to show
    something than nothing for a very old or instrumentation-predates-this
    account.
    """
    session_id = None
    for event in events_newest_first:
        if event.get("eventType") == "session_start":
            session_id = event.get("sessionId")
            break

    if session_id is None:
        return None, list(reversed(events_newest_first))

    matching = [e for e in events_newest_first if e.get("sessionId") == session_id]
    return session_id, list(reversed(matching))


def _format_timeline(events: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    questions: dict[str, dict[str, Any]] = {}
    question_order: list[str] = []
    saw_session_end = False

    for event in events:
        event_type = event.get("eventType")
        data = event.get("data", {})

        if event_type == "session_start":
            lines.append(f"[{event['timestamp']}] Session started")

        elif event_type == "question_shown":
            question_id = data.get("questionId", "?")
            questions[question_id] = {
                "subtopic": data.get("subtopic", "?"),
                "tier": data.get("tier", "?"),
                "attempts": [],
            }
            question_order.append(question_id)

        elif event_type == "answer_submitted":
            question_id = data.get("questionId", "?")
            questions.setdefault(question_id, {"subtopic": "?", "tier": "?", "attempts": []})
            questions[question_id]["attempts"].append(data)

        elif event_type == "worked_example_shown":
            lines.append(f"[{event['timestamp']}]   -> saw the worked example")

        elif event_type == "worked_example_dismissed":
            lines.append(f"[{event['timestamp']}]   -> moved on from the worked example")

        elif event_type == "tier_change":
            lines.append(
                f"[{event['timestamp']}] Tier {data.get('direction', '?')}: "
                f"{data.get('subtopic', '?')} {data.get('from', '?')} -> {data.get('to', '?')}"
            )

        elif event_type == "block_complete":
            lines.append(f"[{event['timestamp']}] Block complete ({data.get('questionsToday', '?')} today)")

        elif event_type == "session_end":
            lines.append(f"[{event['timestamp']}] Session ended")
            saw_session_end = True

    # Interleave question summaries in the order they were shown, after the
    # header-level lines above so the timeline reads start-to-finish.
    question_lines = []
    for question_id in question_order:
        q = questions[question_id]
        attempts = q["attempts"]
        attempt_count = len(attempts)
        final = attempts[-1] if attempts else None
        outcome = "correct" if final and final.get("correct") else "incorrect" if final else "unanswered"
        time_taken = f"{final['millisecondsSinceShown']}ms" if final and final.get("millisecondsSinceShown") is not None else "?"
        question_lines.append(
            f"  Q ({q['subtopic']}, tier={q['tier']}): {attempt_count} attempt(s), {outcome}, {time_taken}"
        )

    lines.extend(question_lines)

    if not saw_session_end:
        lines.append("(no session_end recorded — session appears still open or abandoned)")

    return "\n".join(lines) if lines else "(no events)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, help="Cognito sub — the same id every table is keyed on")
    parser.add_argument("--table-name", default="AxiomSessionEvents")
    parser.add_argument("--region", default="eu-west-1")
    args = parser.parse_args()

    events_newest_first = _fetch_recent_events(table_name=args.table_name, region=args.region, user_id=args.user_id)
    if not events_newest_first:
        print(f"No events found for user {args.user_id}.")
        return

    session_id, session_events = _most_recent_session_events(events_newest_first)
    if session_id:
        print(f"Most recent session ({session_id}):\n")
    else:
        print(f"No session_start found in the last {_RECENT_EVENTS_LIMIT} events — showing everything fetched:\n")

    print(_format_timeline(session_events))


if __name__ == "__main__":
    main()
