"""POST /session/answer — grade a submitted answer, record the attempt, and
advance her tier/badges/daily streak accordingly.

The full diagnostic offer (see-why / try-another, nudge escalation after two
same-prerequisite misses) is Milestone 6 — this returns whether she was
right and the correct answer, plus enough progress state for the UI to show
immediate feedback (tier change, a badge just earned, the daily streak).
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from typing import Any

import boto3

from axiom.diagnostics import build_diagnostic_offer, next_subtopic_miss_count
from axiom.grading import UnparseableAnswer, check_answer
from axiom.progress import (
    TierState,
    advance_after_answer,
    mastery_badge_earned,
    qualifies_for_intro_badge,
    qualifies_for_mastery_streak_today,
)
from axiom.streaks import StreakState, record_attempt

_questions_table = boto3.resource("dynamodb").Table(os.environ["QUESTIONS_TABLE"])
_attempts_table = boto3.resource("dynamodb").Table(os.environ["ATTEMPTS_TABLE"])
_progress_table = boto3.resource("dynamodb").Table(os.environ["PROGRESS_TABLE"])
_streaks_table = boto3.resource("dynamodb").Table(os.environ["STREAKS_TABLE"])


def _user_id(event: dict[str, Any]) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def _tier_state_from_item(item: dict[str, Any] | None) -> TierState:
    if item is None:
        return TierState()
    return TierState(tier=item.get("tier", "intro"), streak=int(item.get("tierStreak", 0)), misses=int(item.get("tierMisses", 0)))


def _streak_state_from_item(item: dict[str, Any] | None) -> StreakState:
    if item is None:
        return StreakState()
    return StreakState(
        current_daily_streak=int(item.get("currentDailyStreak", 0)),
        longest_streak=int(item.get("longestStreak", 0)),
        last_active_date=date.fromisoformat(item["lastActiveDate"]) if item.get("lastActiveDate") else None,
        free_days_used_this_week=int(item.get("freeDaysUsedThisWeek", 0)),
        week_start=date.fromisoformat(item["weekStart"]) if item.get("weekStart") else None,
        questions_today=int(item.get("questionsToday", 0)),
        questions_today_date=(
            date.fromisoformat(item["questionsTodayDate"]) if item.get("questionsTodayDate") else None
        ),
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    user_id = _user_id(event)
    body = json.loads(event.get("body") or "{}")
    question_id = body.get("questionId")
    submitted = body.get("answer", "")

    question_item = _questions_table.get_item(Key={"questionId": question_id}).get("Item")
    if question_item is None:
        return _response(404, {"error": "That question wasn't found — it may have expired."})
    if question_item.get("userId") != user_id:
        return _response(403, {"error": "That's not your question."})

    try:
        correct = check_answer(question_item["answerType"], submitted, question_item["answer"])
    except UnparseableAnswer:
        return _response(400, {"error": "Couldn't read that as an answer — check the formatting and try again."})

    today = datetime.now(timezone.utc).date()
    topic_id = question_item["topicId"]

    _attempts_table.put_item(
        Item={
            "userId": user_id,
            "timestamp": str(time.time()),
            "questionId": question_id,
            "topicId": topic_id,
            "subtopic": question_item["subtopic"],
            "difficulty": question_item["difficulty"],
            "correct": correct,
            "submittedAnswer": submitted,
        }
    )

    # --- tier, badges, topic progress ---
    progress_item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item")
    tier_state = advance_after_answer(_tier_state_from_item(progress_item), correct)

    intro_badge_earned = bool((progress_item or {}).get("introBadgeEarned", False))
    mastery_streak_days = set((progress_item or {}).get("masteryStreakDays", []))

    if correct and qualifies_for_intro_badge(tier_state.tier, tier_state.streak):
        intro_badge_earned = True
    if correct and qualifies_for_mastery_streak_today(tier_state.tier, tier_state.streak):
        mastery_streak_days.add(today.isoformat())
    mastery_badge = mastery_badge_earned(len(mastery_streak_days))

    new_progress_item: dict[str, Any] = {
        "userId": user_id,
        "topicId": topic_id,
        "tier": tier_state.tier,
        "tierStreak": tier_state.streak,
        "tierMisses": tier_state.misses,
        "questionsAnswered": int((progress_item or {}).get("questionsAnswered", 0)) + 1,
        "correctCount": int((progress_item or {}).get("correctCount", 0)) + (1 if correct else 0),
        "introBadgeEarned": intro_badge_earned,
        "masteryBadgeEarned": mastery_badge,
        "lastPracticedAt": datetime.now(timezone.utc).isoformat(),
    }
    if mastery_streak_days:
        new_progress_item["masteryStreakDays"] = mastery_streak_days

    subtopic = question_item["subtopic"]
    subtopic_misses = dict((progress_item or {}).get("subtopicMisses", {}))
    new_miss_count = next_subtopic_miss_count(int(subtopic_misses.get(subtopic, 0)), correct)
    subtopic_misses[subtopic] = new_miss_count
    new_progress_item["subtopicMisses"] = subtopic_misses

    _progress_table.put_item(Item=new_progress_item)

    diagnostic_offer = None if correct else build_diagnostic_offer(subtopic, new_miss_count)

    # --- daily streak ---
    streak_item = _streaks_table.get_item(Key={"userId": user_id}).get("Item")
    streak_state = record_attempt(_streak_state_from_item(streak_item), today)

    new_streak_item: dict[str, Any] = {
        "userId": user_id,
        "currentDailyStreak": streak_state.current_daily_streak,
        "longestStreak": streak_state.longest_streak,
        "freeDaysUsedThisWeek": streak_state.free_days_used_this_week,
        "questionsToday": streak_state.questions_today,
    }
    if streak_state.last_active_date:
        new_streak_item["lastActiveDate"] = streak_state.last_active_date.isoformat()
    if streak_state.week_start:
        new_streak_item["weekStart"] = streak_state.week_start.isoformat()
    if streak_state.questions_today_date:
        new_streak_item["questionsTodayDate"] = streak_state.questions_today_date.isoformat()
    _streaks_table.put_item(Item=new_streak_item)

    return _response(
        200,
        {
            "correct": correct,
            "correctAnswer": question_item["answer"],
            "diagnosticOffer": diagnostic_offer,
            "progress": {
                "tier": tier_state.tier,
                "introBadgeEarned": intro_badge_earned,
                "masteryBadgeEarned": mastery_badge,
            },
            "dailyStreak": streak_state.current_daily_streak,
        },
    )
