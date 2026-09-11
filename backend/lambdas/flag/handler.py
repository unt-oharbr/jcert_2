"""Stub handler for /flag — wiring only, real logic lands in a later milestone."""

import json


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "flag stub — not yet implemented"}),
    }
