from axiom.geometry import (
    Point,
    is_parallel,
    is_perpendicular,
    matches_mx_negative_one_misconception,
    perpendicular_slope,
    slope,
)


def test_slope_basic():
    assert slope(Point(0, 0), Point(2, 4)) == 2


def test_slope_vertical_line_is_none():
    assert slope(Point(3, 0), Point(3, 5)) is None


def test_perpendicular_slope_is_negative_reciprocal_not_sign_flip():
    # This is the seed example: gradient 2 -> perpendicular is -0.5, not -2.
    assert perpendicular_slope(2) == -0.5
    assert perpendicular_slope(2) != -2


def test_perpendicular_slope_horizontal_and_vertical():
    assert perpendicular_slope(0) is None  # horizontal <-> vertical
    assert perpendicular_slope(None) == 0.0


def test_is_perpendicular_true_for_negative_reciprocal():
    assert is_perpendicular(2, -0.5) is True


def test_is_perpendicular_false_for_the_common_misconception():
    # m * -1 instead of -1/m: looks plausible, is wrong.
    assert is_perpendicular(2, -2) is False


def test_is_perpendicular_horizontal_vertical_pair():
    assert is_perpendicular(0, None) is True
    assert is_perpendicular(None, 0) is True


def test_is_parallel():
    assert is_parallel(3, 3) is True
    assert is_parallel(3, -3) is False
    assert is_parallel(None, None) is True  # two vertical lines
    assert is_parallel(None, 5) is False


def test_matches_mx_negative_one_misconception_flags_the_sign_flip():
    assert matches_mx_negative_one_misconception(m=2, submitted=-2) is True


def test_matches_mx_negative_one_misconception_ignores_the_correct_answer():
    assert matches_mx_negative_one_misconception(m=2, submitted=-0.5) is False


def test_matches_mx_negative_one_misconception_ignores_unrelated_wrong_answers():
    # Wrong, but not *this* specific mistake — shouldn't be tagged as it.
    assert matches_mx_negative_one_misconception(m=2, submitted=7) is False
