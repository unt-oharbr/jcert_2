"""Merge every topic's content/<topic>/worked_examples.yaml into a single
axiom/data/worked_examples.json — the reviewed YAML files stay the single
source of truth (and stay easy for a human to read/edit); this JSON is what
axiom.diagnostics actually loads at runtime, since the Lambda layer only
bundles sympy, not pyyaml, and JSON needs no extra dependency at all.

Subtopic ids are unique across topics by construction, so the merged file
stays a flat {subtopic: {title, explanation, example}} map and
axiom.diagnostics.get_worked_example(subtopic)'s signature doesn't need to
know which topic a subtopic belongs to.

Run after editing any topic's YAML:
    uv run python scripts/build_worked_examples.py

app.py also regenerates this automatically on every synth/deploy, so a
stale JSON only affects local pytest runs until this is re-run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent
_CONTENT_DIR = _ROOT / "content"
_OUTPUT = _ROOT / "axiom" / "data" / "worked_examples.json"


def build() -> None:
    merged: dict[str, dict[str, str]] = {}
    for source in sorted(_CONTENT_DIR.glob("*/worked_examples.yaml")):
        topic_examples = yaml.safe_load(source.read_text())
        overlap = set(topic_examples) & set(merged)
        if overlap:
            raise ValueError(f"Subtopic id(s) {overlap} defined in more than one topic's worked_examples.yaml")
        merged.update(topic_examples)

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(json.dumps(merged, indent=2, sort_keys=False))


if __name__ == "__main__":
    sys.path.insert(0, str(_ROOT))
    build()
    print(f"Wrote {_OUTPUT}")
