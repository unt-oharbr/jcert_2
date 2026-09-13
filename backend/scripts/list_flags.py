"""Print flagged questions, newest first — the terminal-only substitute for
an admin console that doesn't exist yet (see docs/misconceptions.md for the
same "no console" gap on the diagnostics side, and scripts/session_report.py
for T4's equivalent).

For each flag, actually re-runs the generator with the stored seed and
prints the reproduced prompt/answer — proof the question can be
regenerated exactly, not just a claim that the stored numbers would allow
it.

Usage:
    uv run python scripts/list_flags.py
    uv run python scripts/list_flags.py --topic-id algebra_equations
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

import boto3

sys.path.insert(0, str(Path(__file__).parent.parent))  # so `axiom` resolves when run as a script

from axiom.topics import TOPICS


def _fetch_all_flags(*, table_name: str, region: str) -> list[dict[str, Any]]:
    # Flags has no GSI for "every flag regardless of question" — a Scan is
    # the only option, and it's fine at this app's volume (a single family,
    # not a production-scale flag queue).
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return items


def _reproduce(flag: dict[str, Any]) -> str:
    seed = flag.get("seed")
    topic_id = flag.get("topicId")
    subtopic = flag.get("subtopic")
    difficulty = flag.get("difficulty")

    if seed is None:
        return "(no seed stored — this question predates T7, can't be regenerated exactly)"
    if topic_id not in TOPICS:
        return f"(unknown topicId '{topic_id}' — can't regenerate)"

    try:
        question = TOPICS[topic_id].generate(subtopic, difficulty, random.Random(seed))
    except Exception as exc:  # noqa: BLE001 — deliberately broad: one old flag whose
        # generator code has since changed shouldn't crash the report for every
        # other flag; the exception is shown inline, not swallowed silently.
        return f"(regeneration failed: {exc})"

    match = question.prompt == flag.get("prompt") and question.answer == flag.get("canonicalAnswer")
    marker = "matches stored prompt/answer" if match else "DIFFERS from stored prompt/answer — generator code changed since this was flagged"
    return f'"{question.prompt}" -> {question.answer}  ({marker})'


def _print_flag(flag: dict[str, Any]) -> None:
    print(f"[{flag.get('timestamp', '?')}] {flag.get('reason', '?')} — {flag.get('topicId', '?')}/{flag.get('subtopic', '?')} (tier={flag.get('difficulty', '?')})")
    print(f"  questionId: {flag.get('questionId', '?')}")
    if flag.get("note"):
        print(f"  note: {flag['note']}")
    print(f"  she submitted: {flag.get('submittedAnswer', '')!r}  correct answer: {flag.get('canonicalAnswer', '?')!r}")
    print(f"  reproduced: {_reproduce(flag)}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-name", default="AxiomFlags")
    parser.add_argument("--region", default="eu-west-1")
    parser.add_argument("--topic-id", default=None, help="Only show flags for this topic")
    args = parser.parse_args()

    flags = _fetch_all_flags(table_name=args.table_name, region=args.region)
    if args.topic_id:
        flags = [f for f in flags if f.get("topicId") == args.topic_id]

    if not flags:
        print("No flags found.")
        return

    flags.sort(key=lambda f: f.get("timestamp", ""), reverse=True)
    for flag in flags:
        _print_flag(flag)


if __name__ == "__main__":
    main()
