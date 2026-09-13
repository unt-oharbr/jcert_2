import pytest

from axiom.progress import (
    TIER_ORDER,
    TierState,
    advance_after_answer,
    mastery_badge_earned,
    overall_progress_fraction,
    qualifies_for_intro_badge,
    qualifies_for_mastery_streak_today,
    topic_progress_fraction,
)


def test_three_correct_in_a_row_advances_a_tier():
    state = TierState(tier="intro", streak=0, misses=0)
    for _ in range(3):
        state = advance_after_answer(state, correct=True)
    assert state.tier == "standard"
    assert state.streak == 0  # resets on advance


def test_full_tier_does_not_advance_further():
    state = TierState(tier="full", streak=10, misses=0)
    state = advance_after_answer(state, correct=True)
    assert state.tier == "full"


def test_two_wrong_in_a_row_demotes_a_tier():
    state = TierState(tier="standard", streak=0, misses=0)
    state = advance_after_answer(state, correct=False)
    assert state.tier == "standard"  # only one miss so far
    state = advance_after_answer(state, correct=False)
    assert state.tier == "intro"


def test_intro_tier_does_not_demote_further():
    state = TierState(tier="intro", streak=0, misses=5)
    state = advance_after_answer(state, correct=False)
    assert state.tier == "intro"


def test_demotion_suspended_does_not_demote_on_two_wrong_in_a_row():
    state = TierState(tier="standard", streak=0, misses=0)
    state = advance_after_answer(state, correct=False, demotion_suspended=True)
    state = advance_after_answer(state, correct=False, demotion_suspended=True)
    assert state.tier == "standard"


def test_demotion_suspended_does_not_load_the_miss_counter_for_later():
    # A frozen (not reset-to-zero) miss counter would silently combine with
    # misses recorded once suspension lifts (e.g. the next day) and demote
    # her for two unrelated mistakes that were never meant to count together.
    state = TierState(tier="standard", streak=0, misses=0)
    state = advance_after_answer(state, correct=False, demotion_suspended=True)
    assert state.misses == 0


def test_demotion_suspended_still_allows_advancement():
    state = TierState(tier="standard", streak=0, misses=0)
    state = advance_after_answer(state, correct=False, demotion_suspended=True)  # a miss, but suspended
    for _ in range(3):
        state = advance_after_answer(state, correct=True, demotion_suspended=True)
    assert state.tier == "full"


def test_a_correct_answer_resets_the_miss_counter():
    state = TierState(tier="standard", streak=0, misses=1)
    state = advance_after_answer(state, correct=True)
    assert state.misses == 0


@pytest.mark.parametrize("tier", ["standard", "full"])
def test_intro_badge_qualifies_at_standard_or_full_with_five_streak(tier: str):
    assert qualifies_for_intro_badge(tier, 5) is True


def test_intro_badge_does_not_qualify_at_intro_tier():
    assert qualifies_for_intro_badge("intro", 5) is False


def test_intro_badge_needs_the_full_streak_length():
    assert qualifies_for_intro_badge("standard", 4) is False


def test_mastery_streak_today_only_counts_at_full_tier():
    assert qualifies_for_mastery_streak_today("standard", 5) is False
    assert qualifies_for_mastery_streak_today("full", 5) is True


def test_mastery_badge_needs_at_least_two_distinct_days():
    assert mastery_badge_earned(1) is False
    assert mastery_badge_earned(2) is True


def test_topic_progress_fraction_starts_each_tier_at_its_floor():
    assert topic_progress_fraction("intro", tier_streak=0, has_mastery_badge=False) == pytest.approx(0.0)
    assert topic_progress_fraction("standard", tier_streak=0, has_mastery_badge=False) == pytest.approx(1 / 3)
    assert topic_progress_fraction("full", tier_streak=0, has_mastery_badge=False) == pytest.approx(2 / 3)


def test_topic_progress_fraction_creeps_up_with_streak_within_a_tier():
    # A streak building toward the next tier should visibly move the bar,
    # not leave it frozen at the tier's floor until the tier actually flips.
    zero = topic_progress_fraction("intro", tier_streak=0, has_mastery_badge=False)
    one = topic_progress_fraction("intro", tier_streak=1, has_mastery_badge=False)
    two = topic_progress_fraction("intro", tier_streak=2, has_mastery_badge=False)
    assert zero < one < two < topic_progress_fraction("standard", tier_streak=0, has_mastery_badge=False)


def test_mastery_badge_fills_the_bar_completely():
    assert topic_progress_fraction("intro", tier_streak=0, has_mastery_badge=True) == 1.0


def test_overall_progress_is_the_average_across_topics():
    assert overall_progress_fraction([1.0, 0.5]) == pytest.approx(0.75)


def test_overall_progress_with_no_topics_is_zero():
    assert overall_progress_fraction([]) == 0.0


def test_tier_order_is_the_expected_three_tiers():
    assert TIER_ORDER == ["intro", "standard", "full"]
