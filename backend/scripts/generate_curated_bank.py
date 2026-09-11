"""Freeze a fixed-seed snapshot of axiom/question_generators.py for regression testing.

This is NOT the live question pool — the /session/next-question Lambda
calls the same generator functions directly, with fresh random numbers,
for every real request (see question_generators.py's module docstring for
why). This script exists purely to produce a reproducible YAML fixture that
tests/test_curated_bank.py independently re-checks; if that suite passes,
the generators are trusted for live use too, since it's the exact same code.

Run with:
    uv run python scripts/generate_curated_bank.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))  # so `axiom` resolves when run as a script

from axiom.question_generators import SUBTOPICS, TIERS, generate  # noqa: E402

_QUESTIONS_PER_CELL = 3
_SEED = 20260910
_OUTPUT_PATH = Path(__file__).parent.parent / "content" / "coordinate_geometry_line" / "questions.yaml"


def build_fixture() -> list[dict]:
    rng = random.Random(_SEED)
    fixture: list[dict] = []
    for subtopic in SUBTOPICS:
        for tier in TIERS:
            for i in range(1, _QUESTIONS_PER_CELL + 1):
                question = generate(subtopic, tier, rng)
                fixture.append({"id": f"cgl-{subtopic}-{tier}-{i:02d}", **asdict(question)})
    return fixture


def main() -> None:
    fixture = build_fixture()
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT_PATH.open("w") as f:
        yaml.safe_dump(fixture, f, sort_keys=False, allow_unicode=True)
    print(f"Wrote {len(fixture)} questions to {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
