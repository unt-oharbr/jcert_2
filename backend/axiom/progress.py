"""Difficulty progression, badge eligibility, and topic/overall progress bars.

Tier advancement is a small, explicit state machine rather than anything
adaptive-feeling-clever: 3 correct in a row at a tier moves her up one tier;
2 wrong in a row at a tier drops her back one. Badges are two deliberately
different bars — an easy first win, and a real mastery bar that needs
repeated proof, not a lucky streak.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

TIER_ORDER = ["intro", "standard", "full"]

_ADVANCE_AFTER_STREAK = 3
_DEMOTE_AFTER_MISSES = 2

INTRO_BADGE_TIERS = {"standard", "full"}
INTRO_BADGE_STREAK = 5

MASTERY_BADGE_TIER = "full"
MASTERY_BADGE_STREAK = 5
MASTERY_BADGE_MIN_DAYS = 2


@dataclass(frozen=True)
class TierState:
    tier: str = TIER_ORDER[0]
    streak: int = 0  # consecutive correct at the current tier
    misses: int = 0  # consecutive incorrect at the current tier


def advance_after_answer(state: TierState, correct: bool, *, demotion_suspended: bool = False) -> TierState:
    """`demotion_suspended` is set once she's deep into a long session (see
    the answer handler) — a tired mistake late on shouldn't cost her a tier.
    Advancement is unaffected; a wrong answer still clears the advance streak,
    it just doesn't count toward (or load) the miss counter, so it can't
    demote today and can't quietly demote tomorrow either."""
    index = TIER_ORDER.index(state.tier)
    if correct:
        streak = state.streak + 1
        if streak >= _ADVANCE_AFTER_STREAK and index < len(TIER_ORDER) - 1:
            return TierState(tier=TIER_ORDER[index + 1], streak=0, misses=0)
        return replace(state, streak=streak, misses=0)

    if demotion_suspended:
        return replace(state, streak=0)

    misses = state.misses + 1
    if misses >= _DEMOTE_AFTER_MISSES and index > 0:
        return TierState(tier=TIER_ORDER[index - 1], streak=0, misses=0)
    return replace(state, streak=0, misses=misses)


def qualifies_for_intro_badge(tier: str, streak: int) -> bool:
    return tier in INTRO_BADGE_TIERS and streak >= INTRO_BADGE_STREAK


def qualifies_for_mastery_streak_today(tier: str, streak: int) -> bool:
    return tier == MASTERY_BADGE_TIER and streak >= MASTERY_BADGE_STREAK


def mastery_badge_earned(distinct_mastery_days: int) -> bool:
    return distinct_mastery_days >= MASTERY_BADGE_MIN_DAYS


def topic_progress_fraction(tier: str, tier_streak: int, has_mastery_badge: bool) -> float:
    """How full a topic's progress bar should look.

    Tier alone only has 3 possible values (33/66/100%), which looks and
    feels frozen between tier-ups — this blends in how close her current
    streak is to the next tier, so the bar visibly creeps forward with
    every correct answer instead of sitting flat until a 3-in-a-row lands.
    """
    if has_mastery_badge:
        return 1.0
    tier_index = TIER_ORDER.index(tier)
    tier_span = 1 / len(TIER_ORDER)
    within_tier = min(tier_streak, _ADVANCE_AFTER_STREAK) / _ADVANCE_AFTER_STREAK
    return (tier_index + within_tier) * tier_span


def overall_progress_fraction(topic_fractions: list[float]) -> float:
    if not topic_fractions:
        return 0.0
    return sum(topic_fractions) / len(topic_fractions)
