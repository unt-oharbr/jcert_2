import pytest

from axiom.grading import UnparseableAnswer, check_answer


def test_value_accepts_equivalent_fraction_and_decimal():
    assert check_answer("value", "3.5", "7/2") is True


def test_value_accepts_simplified_surd_forms():
    assert check_answer("value", "2*sqrt(2)", "sqrt(8)") is True


def test_value_rejects_a_genuinely_different_number():
    assert check_answer("value", "4", "7/2") is False


def test_point_accepts_decimal_vs_fraction_coordinates():
    assert check_answer("point", "(2.5, 5.5)", "(5/2, 11/2)") is True


def test_point_rejects_a_different_point():
    assert check_answer("point", "(2, 5)", "(5/2, 11/2)") is False


def test_equation_accepts_loose_formatting():
    assert check_answer("equation", "y=2x-1", "y = 2*x - 1") is True


def test_equation_accepts_decimal_slope_matching_a_fraction():
    assert check_answer("equation", "y=-0.5x+3", "y = -1/2*x + 3") is True


def test_equation_rejects_wrong_slope():
    # Exactly the seed misconception: -2 instead of -1/2.
    assert check_answer("equation", "y = -2*x + 3", "y = -1/2*x + 3") is False


def test_equation_rejects_wrong_intercept():
    assert check_answer("equation", "y = -1/2*x + 99", "y = -1/2*x + 3") is False


def test_unparseable_value_raises_not_just_false():
    # A bare word like "banana" is actually valid to sympy (it just reads as
    # a variable name) — this needs genuinely invalid syntax to fail parsing.
    with pytest.raises(UnparseableAnswer):
        check_answer("value", "3 + + +", "5")


def test_equation_without_equals_sign_raises():
    with pytest.raises(UnparseableAnswer):
        check_answer("equation", "2x - 1", "y = 2*x - 1")


def test_unknown_answer_type_raises():
    with pytest.raises(ValueError):
        check_answer("essay", "anything", "anything")


def test_factored_expression_accepts_the_correct_factorisation():
    assert check_answer("factored_expression", "3(2x + 3)", "3(2x + 3)") is True


def test_factored_expression_accepts_loose_formatting():
    assert check_answer("factored_expression", "3*(2*x+3)", "3(2x + 3)") is True


def test_factored_expression_rejects_giving_back_the_unfactored_form():
    # This is the whole point of this checker: mathematically equal to the
    # canonical answer, but she hasn't actually factored anything.
    assert check_answer("factored_expression", "6x + 9", "3(2x + 3)") is False


def test_factored_expression_rejects_a_wrong_factorisation():
    assert check_answer("factored_expression", "3(2x + 5)", "3(2x + 3)") is False


def test_factored_expression_accepts_quadratic_factor_pairs_in_either_order():
    assert check_answer("factored_expression", "(x - 3)(x - 2)", "(x - 2)(x - 3)") is True


def test_root_set_accepts_either_order():
    assert check_answer("root_set", "x = 3 or x = 2", "x = 2 or x = 3") is True


def test_root_set_accepts_comma_separated_without_x_equals():
    assert check_answer("root_set", "2, 3", "x = 2 or x = 3") is True


def test_root_set_rejects_a_missing_root():
    assert check_answer("root_set", "x = 2", "x = 2 or x = 3") is False


def test_root_set_rejects_a_wrong_root():
    assert check_answer("root_set", "x = 2 or x = 4", "x = 2 or x = 3") is False


def test_inequality_accepts_loose_formatting():
    assert check_answer("inequality", "x<4", "x < 4") is True


def test_inequality_rejects_the_forgot_to_flip_sign_misconception():
    assert check_answer("inequality", "x < -2", "x > -2") is False


def test_inequality_rejects_wrong_boundary():
    assert check_answer("inequality", "x < 4", "x < 5") is False


def test_inequality_without_x_raises():
    with pytest.raises(UnparseableAnswer):
        check_answer("inequality", "4", "x < 4")
