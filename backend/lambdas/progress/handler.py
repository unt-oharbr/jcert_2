"""GET /progress — her per-topic and overall progress, badges, and streak."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from axiom.progress import overall_progress_fraction, topic_progress_fraction
from axiom.topics import TOPICS

_progress_table = boto3.resource("dynamodb").Table(os.environ["PROGRESS_TABLE"])
_streaks_table = boto3.resource("dynamodb").Table(os.environ["STREAKS_TABLE"])


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)

    streak_item = _streaks_table.get_item(Key={"userId": user_id}).get("Item") or {}

    topics = []
    for topic_id, topic in TOPICS.items():
        progress_item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item") or {}
        tier = progress_item.get("tier", "intro")
        tier_streak = int(progress_item.get("tierStreak", 0))
        mastery_badge = bool(progress_item.get("masteryBadgeEarned", False))

        topics.append(
            {
                "topicId": topic_id,
                "label": topic.TOPIC_LABEL,
                "tier": tier,
                "progress": topic_progress_fraction(tier, tier_streak, mastery_badge),
                "introBadgeEarned": bool(progress_item.get("introBadgeEarned", False)),
                "masteryBadgeEarned": mastery_badge,
                "questionsAnswered": int(progress_item.get("questionsAnswered", 0)),
            }
        )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "topics": topics,
                "overallProgress": overall_progress_fraction([t["progress"] for t in topics]),
                "dailyStreak": int(streak_item.get("currentDailyStreak", 0)),
                "longestStreak": int(streak_item.get("longestStreak", 0)),
            }
        ),
    }
