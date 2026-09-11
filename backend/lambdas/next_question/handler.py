"""POST /session/next-question — generate and serve a fresh question instance
at her current difficulty tier.

Picks a random topic/subtopic by default. After a wrong answer, the client
instead asks for another instance of the *same* subtopic (optional
`topicId`/`subtopic` in the request body) — a slip or a gap both deserve a
similar question to actually retry, not a random new one that proves
nothing either way.
"""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from typing import Any

import boto3

from axiom.topics import TOPICS

_SERVED_TTL_SECONDS = 60 * 60 * 24  # a day is more than enough to answer or abandon a question

_questions_table = boto3.resource("dynamodb").Table(os.environ["QUESTIONS_TABLE"])
_progress_table = boto3.resource("dynamodb").Table(os.environ["PROGRESS_TABLE"])


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _current_tier(user_id: str, topic_id: str) -> str:
    item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item")
    return item.get("tier", "intro") if item else "intro"


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)
    body = json.loads(event.get("body") or "{}")
    requested_topic_id = body.get("topicId")
    requested_subtopic = body.get("subtopic")

    if requested_topic_id in TOPICS and requested_subtopic in TOPICS[requested_topic_id].SUBTOPICS:
        topic_id, topic = requested_topic_id, TOPICS[requested_topic_id]
        subtopic = requested_subtopic
    else:
        topic_id, topic = random.choice(list(TOPICS.items()))
        subtopic = random.choice(topic.SUBTOPICS)

    tier = _current_tier(user_id, topic_id)
    question = topic.generate(subtopic, tier, random.Random())

    question_id = str(uuid.uuid4())
    _questions_table.put_item(
        Item={
            "questionId": question_id,
            "userId": user_id,
            "topicId": topic_id,
            "subtopic": question.subtopic,
            "difficulty": question.difficulty,
            "answerType": question.answer_type,
            "answer": question.answer,
            "commonWrongAnswers": question.common_wrong_answers,
            "ttl": int(time.time()) + _SERVED_TTL_SECONDS,
        }
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "questionId": question_id,
                "topicId": topic_id,
                "topicLabel": topic.TOPIC_LABEL,
                "subtopic": question.subtopic,
                "difficulty": question.difficulty,
                "type": question.type,
                "answerType": question.answer_type,
                "prompt": question.prompt,
                # Not every topic's Question has this attribute (only the
                # coordinate-geometry generators produce one) — getattr
                # keeps this handler from needing to know which topics do.
                "visualization": getattr(question, "visualization", None),
            }
        ),
    }
