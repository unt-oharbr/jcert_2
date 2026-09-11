"""Ask-first diagnostic: offer, don't force, a trip to the prerequisite.

A wrong answer is often a slip, not a gap — forcing an explanation every
time would feel like being talked down to. But after two misses in a row
on the same subtopic, the neutral offer becomes a nudge, since pure
neutrality just lets her keep declining the explanation she actually needs.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

NUDGE_AFTER_MISSES = 2

_WORKED_EXAMPLES_PATH = Path(__file__).parent / "data" / "worked_examples.json"


class WorkedExample(TypedDict):
    title: str
    explanation: str
    example: str


@lru_cache(maxsize=1)
def _worked_examples() -> dict[str, WorkedExample]:
    return json.loads(_WORKED_EXAMPLES_PATH.read_text())


def get_worked_example(subtopic: str) -> WorkedExample | None:
    """The "see why" content for a subtopic, or None if it's not recognised."""
    return _worked_examples().get(subtopic)


class DiagnosticOffer(TypedDict):
    available: bool
    prerequisiteNodeId: str
    nudge: bool


def next_subtopic_miss_count(current: int, correct: bool) -> int:
    """A correct answer clears the slate; a wrong one extends it."""
    return 0 if correct else current + 1


def build_diagnostic_offer(subtopic: str, miss_count: int) -> DiagnosticOffer:
    return {
        "available": True,
        "prerequisiteNodeId": subtopic,
        "nudge": miss_count >= NUDGE_AFTER_MISSES,
    }
