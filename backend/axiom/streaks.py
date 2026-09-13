"""Daily practice streak, with one missed-day free pass per week.

A day counts once she's answered DAILY_QUESTION_TARGET questions — right or
wrong, showing up and doing the work is what's being reinforced, not
getting everything correct. One missed day doesn't break the streak, but a
second miss in the same week does, and two missed days in a row always
breaks it (the free pass only covers a single gap).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

DAILY_QUESTION_TARGET = 5


@dataclass(frozen=True)
class StreakState:
    current_daily_streak: int = 0
    longest_streak: int = 0
    last_active_date: date | None = None
    free_days_used_this_week: int = 0
    week_start: date | None = None
    questions_today: int = 0
    questions_today_date: date | None = None


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def record_daily_completion(state: StreakState, today: date) -> StreakState:
    """Call once she's hit her daily question target for `today`."""
    if state.last_active_date == today:
        return state  # already credited today — avoid double-counting

    this_week_start = _week_start(today)
    free_days_used = state.free_days_used_this_week if state.week_start == this_week_start else 0

    if state.last_active_date is None:
        new_streak = 1
    else:
        days_missed = (today - state.last_active_date).days - 1
        if days_missed <= 0:
            new_streak = state.current_daily_streak + 1
        elif days_missed == 1 and free_days_used < 1:
            free_days_used += 1
            new_streak = state.current_daily_streak + 1
        else:
            new_streak = 1

    return replace(
        state,
        current_daily_streak=new_streak,
        longest_streak=max(state.longest_streak, new_streak),
        last_active_date=today,
        free_days_used_this_week=free_days_used,
        week_start=this_week_start,
    )


def record_attempt(state: StreakState, today: date) -> StreakState:
    """Call on every answered question, correct or not."""
    if state.questions_today_date != today:
        state = replace(state, questions_today=0, questions_today_date=today)
    state = replace(state, questions_today=state.questions_today + 1)
    if state.questions_today == DAILY_QUESTION_TARGET:
        state = record_daily_completion(state, today)
    return state
