"""GET/PUT /profile — her nickname, avatar, and colour theme.

The user id comes from the Cognito JWT the HTTP API authorizer already
verified (event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]),
never from the request body — she can only ever read or write her own
profile.
"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from axiom.profile import ProfileValidationError, build_profile

_table = boto3.resource("dynamodb").Table(os.environ["USERS_TABLE"])

_DEFAULT_AVATAR = "comet"
_DEFAULT_COLOUR_THEME = "indigo"


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _get_profile(user_id: str) -> dict[str, Any]:
    item = _table.get_item(Key={"userId": user_id}).get("Item")
    if item is None:
        # First login: no profile yet, so the frontend knows to show
        # first-run setup rather than treating this as an error.
        return {"userId": user_id, "isNew": True}
    return {**item, "isNew": False}


def _put_profile(user_id: str, body: dict[str, Any]) -> dict[str, Any]:
    profile = build_profile(
        user_id=user_id,
        nickname=body.get("nickname", ""),
        avatar=body.get("avatar", _DEFAULT_AVATAR),
        colour_theme=body.get("colourTheme", _DEFAULT_COLOUR_THEME),
    )
    _table.put_item(
        Item={
            "userId": profile.user_id,
            "nickname": profile.nickname,
            "avatar": profile.avatar,
            "colourTheme": profile.colour_theme,
        }
    )
    return {"userId": profile.user_id, "nickname": profile.nickname, "avatar": profile.avatar, "colourTheme": profile.colour_theme}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event["requestContext"]["http"]["method"]
    user_id = _user_id(event)

    if method == "GET":
        return _response(200, _get_profile(user_id))

    if method == "PUT":
        try:
            body = json.loads(event.get("body") or "{}")
            return _response(200, _put_profile(user_id, body))
        except ProfileValidationError as exc:
            return _response(400, {"error": str(exc)})

    return _response(405, {"error": f"Unsupported method {method}"})
