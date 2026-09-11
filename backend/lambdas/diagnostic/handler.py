"""GET /diagnostic/{prerequisiteNodeId} — the "see why" worked-example content."""

from __future__ import annotations

import json
from typing import Any

from axiom.diagnostics import get_worked_example


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    subtopic = event["pathParameters"]["prerequisiteNodeId"]
    example = get_worked_example(subtopic)

    if example is None:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"No worked example for '{subtopic}'."}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(example),
    }
