"""Independently re-derive every generated answer and check it against the
generator's output.

This deliberately does NOT re-use generate_curated_bank.py's own arithmetic —
that would only prove the generator agrees with itself. Instead it re-parses
each question's prompt with its own regexes and recomputes the answer from
scratch (via axiom.geometry, Fraction, or sympy), so a bug shared between
"generate the question" and "check the question" can't hide. Every question
in the bank is checked, not a sample — this is the curated, trusted content
the AI-generated variants get measured against.
"""

from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

import pytest
import yaml
from sympy import Rational, simplify, sympify

from axiom.geometry import Point, is_perpendicular

_CONTENT_DIR = Path(__file__).parent.parent / "content" / "coordinate_geometry_line"
_BANK_PATH = _CONTENT_DIR / "questions.yaml"
_WORKED_EXAMPLES_PATH = _CONTENT_DIR / "worked_examples.yaml"
_POINT_RE = re.compile(r"\((-?\d+),\s*(-?\d+)\)")
_EQUATION_RE = re.compile(r"y = (-?\d+(?:/\d+)?)\*x(?: ([+-]) (\d+(?:/\d+)?))?")


def _load_bank() -> list[dict]:
    return yaml.safe_load(_BANK_PATH.read_text())


def _points_in(text: str) -> list[Point]:
    return [Point(int(x), int(y)) for x, y in _POINT_RE.findall(text)]


def _parse_fraction(s: str) -> Fraction:
    return Fraction(s)


def _parse_point_answer(s: str) -> tuple[Fraction, Fraction]:
    x_str, y_str = s.strip("()").split(",")
    return _parse_fraction(x_str.strip()), _parse_fraction(y_str.strip())


def _parse_equation(text: str) -> tuple[Fraction, Fraction]:
    match = _EQUATION_RE.search(text)
    assert match, f"couldn't parse a 'y = m*x [+/- c]' equation out of: {text!r}"
    m = _parse_fraction(match.group(1))
    if match.group(3) is None:
        c = Fraction(0)
    else:
        c = _parse_fraction(match.group(3))
        if match.group(2) == "-":
            c = -c
    return m, c


@pytest.fixture(scope="module")
def bank() -> dict[str, list[dict]]:
    by_subtopic: dict[str, list[dict]] = {}
    for q in _load_bank():
        by_subtopic.setdefault(q["subtopic"], []).append(q)
    return by_subtopic


def test_every_subtopic_has_a_worked_example(bank: dict[str, list[dict]]) -> None:
    worked_examples = yaml.safe_load(_WORKED_EXAMPLES_PATH.read_text())
    assert set(worked_examples.keys()) == set(bank.keys())
    for subtopic, content in worked_examples.items():
        assert {"title", "explanation", "example"} <= content.keys(), subtopic


def test_bank_has_expected_size(bank: dict[str, list[dict]]) -> None:
    assert sum(len(qs) for qs in bank.values()) == 72
    for subtopic, questions in bank.items():
        assert len(questions) == 9, f"{subtopic} should have 9 questions (3 tiers x 3 each)"


def test_slope_two_points(bank: dict[str, list[dict]]) -> None:
    for q in bank["slope_two_points"]:
        p1, p2 = _points_in(q["prompt"])
        expected = Fraction(p2.y - p1.y, p2.x - p1.x)
        assert _parse_fraction(q["answer"]) == expected, q["id"]


def test_slope_intercept_form(bank: dict[str, list[dict]]) -> None:
    line_re = re.compile(r"The line (-?\d+)x \+ y = (-?\d+)")
    for q in bank["slope_intercept_form"]:
        match = line_re.search(q["prompt"])
        assert match, q["prompt"]
        c = int(match.group(2))
        assert _parse_point_answer(q["answer"]) == (Fraction(0), Fraction(c)), q["id"]


def test_equation_given_point_slope(bank: dict[str, list[dict]]) -> None:
    stem_re = re.compile(r"slope (-?\d+(?:/\d+)?) and passes through the point")
    for q in bank["equation_given_point_slope"]:
        m = _parse_fraction(stem_re.search(q["prompt"]).group(1))
        (point,) = _points_in(q["prompt"])
        answer_m, answer_c = _parse_equation(q["answer"])
        assert answer_m == m, q["id"]
        # The line must actually pass through the given point: y == m*x + c.
        assert Fraction(point.y) == m * Fraction(point.x) + answer_c, q["id"]


def test_parallel_lines(bank: dict[str, list[dict]]) -> None:
    for q in bank["parallel_lines"]:
        k_m, _k_c = _parse_equation(q["prompt"])
        (point,) = _points_in(q["prompt"])
        n_m, n_c = _parse_equation(q["answer"])
        assert n_m == k_m, q["id"]  # parallel => same slope
        assert Fraction(point.y) == n_m * Fraction(point.x) + n_c, q["id"]  # passes through the given point
        # The flagged "reused original intercept" wrong answer must actually be wrong.
        for wrong in q["common_wrong_answers"]:
            assert wrong["answer"] != q["answer"], q["id"]


def test_perpendicular_lines(bank: dict[str, list[dict]]) -> None:
    for q in bank["perpendicular_lines"]:
        k_m, _k_c = _parse_equation(q["prompt"])
        (point,) = _points_in(q["prompt"])
        n_m, n_c = _parse_equation(q["answer"])

        # This is the whole point of the app: -1/m, verified via the same
        # trusted checker axiom/geometry.py already has tests for.
        assert is_perpendicular(float(k_m), float(n_m)), q["id"]
        assert Fraction(point.y) == n_m * Fraction(point.x) + n_c, q["id"]

        wrong = q["common_wrong_answers"][0]
        assert wrong["misconception"] == "mx_negative_one"
        wrong_m, _wrong_c = _parse_equation(wrong["answer"])
        assert wrong_m == -k_m, q["id"]  # the m * -1 mistake, not -1/m
        assert not is_perpendicular(float(k_m), float(wrong_m)), f"{q['id']}: the wrong answer is secretly correct"


def test_midpoint(bank: dict[str, list[dict]]) -> None:
    for q in bank["midpoint"]:
        p1, p2 = _points_in(q["prompt"])
        expected = (Fraction(p1.x + p2.x, 2), Fraction(p1.y + p2.y, 2))
        assert _parse_point_answer(q["answer"]) == expected, q["id"]


def test_distance(bank: dict[str, list[dict]]) -> None:
    for q in bank["distance"]:
        p1, p2 = _points_in(q["prompt"])
        expected = sympify(f"sqrt({(p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2})")
        actual = sympify(q["answer"])
        assert simplify(expected - actual) == 0, q["id"]


def test_axis_intercepts(bank: dict[str, list[dict]]) -> None:
    for q in bank["axis_intercepts"]:
        m, c = _parse_equation(q["prompt"])
        x, y = _parse_point_answer(q["answer"])
        assert y == 0, q["id"]
        assert Rational(0) == Rational(m) * Rational(x) + Rational(c), q["id"]
        assert x != 0, f"{q['id']}: degenerate intercept through the origin slipped through"
