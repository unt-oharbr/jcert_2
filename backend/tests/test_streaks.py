from datetime import date

from axiom.streaks import DAILY_QUESTION_TARGET, StreakState, record_attempt, record_daily_completion


def test_first_ever_completion_starts_streak_at_one():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))
    assert state.current_daily_streak == 1
    assert state.longest_streak == 1


def test_consecutive_days_increment_without_using_a_free_pass():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))
    state = record_daily_completion(state, date(2026, 1, 6))
    assert state.current_daily_streak == 2
    assert state.free_days_used_this_week == 0


def test_completing_twice_in_one_day_does_not_double_count():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))
    state = record_daily_completion(state, date(2026, 1, 5))
    assert state.current_daily_streak == 1


def test_one_missed_day_is_forgiven_by_the_free_pass():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))  # Monday
    state = record_daily_completion(state, date(2026, 1, 7))  # Wednesday — Tuesday missed
    assert state.current_daily_streak == 2
    assert state.free_days_used_this_week == 1


def test_a_second_missed_day_the_same_week_breaks_the_streak():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))  # Monday
    state = record_daily_completion(state, date(2026, 1, 7))  # Wed — free pass used
    state = record_daily_completion(state, date(2026, 1, 9))  # Fri — Thu missed, no pass left
    assert state.current_daily_streak == 1


def test_two_consecutive_missed_days_break_the_streak_even_with_a_free_pass_available():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))  # Monday
    state = record_daily_completion(state, date(2026, 1, 8))  # Thursday — Tue AND Wed missed
    assert state.current_daily_streak == 1


def test_free_pass_resets_each_new_week():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))  # Monday, week 1
    state = record_daily_completion(state, date(2026, 1, 7))  # Wed, uses week 1's free pass
    state = record_daily_completion(state, date(2026, 1, 12))  # Mon, week 2 — big gap, streak resets
    assert state.current_daily_streak == 1
    assert state.free_days_used_this_week == 0  # new week, pass available again

    state = record_daily_completion(state, date(2026, 1, 14))  # Wed, week 2 — one day missed
    assert state.current_daily_streak == 2  # forgiven by week 2's own free pass
    assert state.free_days_used_this_week == 1


def test_longest_streak_survives_a_break():
    state = record_daily_completion(StreakState(), date(2026, 1, 5))
    state = record_daily_completion(state, date(2026, 1, 6))
    state = record_daily_completion(state, date(2026, 1, 7))  # streak of 3
    state = record_daily_completion(state, date(2026, 1, 20))  # big gap, breaks it
    assert state.current_daily_streak == 1
    assert state.longest_streak == 3


def test_record_attempt_only_credits_the_streak_at_the_daily_target():
    state = StreakState()
    today = date(2026, 1, 5)
    for _ in range(DAILY_QUESTION_TARGET - 1):
        state = record_attempt(state, today)
    assert state.current_daily_streak == 0  # not yet at the target
    state = record_attempt(state, today)
    assert state.questions_today == DAILY_QUESTION_TARGET
    assert state.current_daily_streak == 1


def test_record_attempt_resets_the_daily_counter_on_a_new_day():
    state = StreakState()
    today = date(2026, 1, 5)
    for _ in range(DAILY_QUESTION_TARGET):
        state = record_attempt(state, today)
    assert state.questions_today == DAILY_QUESTION_TARGET

    state = record_attempt(state, date(2026, 1, 6))
    assert state.questions_today == 1
