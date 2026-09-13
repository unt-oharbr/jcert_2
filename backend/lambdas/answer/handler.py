"""POST /session/answer — grade a submitted answer, record the attempt, and
advance her tier/badges/daily streak accordingly.

The full diagnostic offer (see-why / try-another, nudge escalation after two
same-prerequisite misses) is Milestone 6 — this returns whether she was
right and the correct answer, plus enough progress state for the UI to show
immediate feedback (tier change, a badge just earned, the daily streak).

Tier demotion is suspended from the 11th question of the day onward (see
docs/spec.md's session-shape rules): a tired mistake deep into a long
session shouldn't cost her a tier. `questions_today` (the same counter the
daily streak already tracks, right or wrong) stands in for "how far into
today's session is this answer" — there's no separate session concept
elsewhere in the backend, so this reuses the one that already exists rather
than inventing a second. Advancement is never suspended.

A wrong first attempt on most subtopics gets one same-question retry before
the worked example appears (Questions items gain a transient `attempts`
field for this — 0/absent until a retry is offered, then 1). A first-attempt
correct counts toward the tier advance as normal; a second-attempt correct
is tier-neutral (doesn't advance, doesn't demote, doesn't reset the advance
streak); wrong twice resolves as a single miss, same as any wrong answer
always has. `_SKIP_RETRY_ANSWER_TYPES` excludes subtopics where a second
guess would be trivially easier than the first without requiring any real
understanding — see that constant's comment.
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

_DEMOTION_SUSPENDED_AFTER_QUESTION = 10  # suspended from the 11th question of the day onward

# Subtopics whose *coded* common wrong answer (axiom.*_generators'
# common_wrong_answers) is a trivial resubmission away from the right one —
# skip the retry there and go straight to the worked example.
#
# `inequalities`: the coded distractor (forgot_to_flip_sign) uses the exact
# same threshold number as the correct answer, differing only in comparison
# direction (< vs >) — she could flip the symbol and resubmit without any
# new understanding.
#
# Considered and excluded: `perpendicular_lines`'s coded distractor
# (mx_negative_one) changes *both* the slope and the back-solved intercept
# relative to the correct answer — not a single flip on the same submitted
# string — so a second guess there isn't materially easier than the first.
_SKIP_RETRY_ANSWER_TYPES = {"inequality"}


def _is_retry_eligible(answer_type: str) -> bool:
    return answer_type not in _SKIP_RETRY_ANSWER_TYPES


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
    is_second_attempt = bool(question_item.get("attempts"))

    if not is_second_attempt and not correct and _is_retry_eligible(question_item["answerType"]):
        _questions_table.update_item(
            Key={"questionId": question_id},
            UpdateExpression="SET attempts = :a",
            ExpressionAttributeValues={":a": 1},
        )
        _attempts_table.put_item(
            Item={
                "userId": user_id,
                "timestamp": str(time.time()),
                "questionId": question_id,
                "topicId": topic_id,
                "subtopic": question_item["subtopic"],
                "difficulty": question_item["difficulty"],
                "correct": False,
                "submittedAnswer": submitted,
                "attemptNumber": 1,
            }
        )
        # Nothing resolved yet — report current state unchanged, with no
        # correct answer, no diagnostic offer, no indication of what was
        # wrong. The frontend keeps showing this same question.
        progress_item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item")
        streak_state = _streak_state_from_item(_streaks_table.get_item(Key={"userId": user_id}).get("Item"))
        return _response(
            200,
            {
                "correct": False,
                "correctAnswer": None,
                "secondAttemptAvailable": True,
                "diagnosticOffer": None,
                "progress": {
                    "tier": (progress_item or {}).get("tier", "intro"),
                    "introBadgeEarned": bool((progress_item or {}).get("introBadgeEarned", False)),
                    "masteryBadgeEarned": bool((progress_item or {}).get("masteryBadgeEarned", False)),
                },
                "dailyStreak": streak_state.current_daily_streak,
                "questionsToday": streak_state.questions_today,
            },
        )

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
            "attemptNumber": 2 if is_second_attempt else 1,
        }
    )

    # --- daily streak (computed first: today's question count decides whether
    # tier demotion is suspended for this answer) ---
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

    # --- tier, badges, topic progress ---
    progress_item = _progress_table.get_item(Key={"userId": user_id, "topicId": topic_id}).get("Item")
    if is_second_attempt and correct:
        # Neutral: she got there on the second try, which is real, but it
        # doesn't count toward the advance streak the way a first-attempt
        # correct does, and it can't demote or reset anything either.
        tier_state = _tier_state_from_item(progress_item)
    else:
        demotion_suspended = streak_state.questions_today > _DEMOTION_SUSPENDED_AFTER_QUESTION
        tier_state = advance_after_answer(
            _tier_state_from_item(progress_item), correct, demotion_suspended=demotion_suspended
        )

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

    return _response(
        200,
        {
            "correct": correct,
            "correctAnswer": question_item["answer"],
            "secondAttemptAvailable": False,
            "diagnosticOffer": diagnostic_offer,
            "progress": {
                "tier": tier_state.tier,
                "introBadgeEarned": intro_badge_earned,
                "masteryBadgeEarned": mastery_badge,
            },
            "dailyStreak": streak_state.current_daily_streak,
            "questionsToday": streak_state.questions_today,
        },
    )
