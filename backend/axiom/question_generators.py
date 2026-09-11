"""Parametric question generators for Coordinate Geometry of the Line.

Every answer is computed from exact Fraction/sympy arithmetic and the
already-tested axiom.geometry module, never hand-typed — this is the
"curated, trusted" content the app leans on. Because each question is a
template with randomised numbers rather than a fixed piece of text, the
Lambda serving her practice session calls `generate()` fresh for every
question instead of pulling from a pre-seeded pool: unlimited variety, and
she can never memorise "the (0,2)-(1,5) one" instead of re-deriving it.

scripts/generate_curated_bank.py uses the same functions with a fixed seed
to produce a frozen YAML fixture — not for live serving, but as a
regression-tested snapshot that tests/test_curated_bank.py independently
re-checks. If that suite passes, live generation is trusted too, since it's
the exact same code.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from fractions import Fraction

from sympy import sqrt as sympy_sqrt

from axiom.geometry import Point, perpendicular_slope

TOPIC_ID = "coordinate_geometry_line"
TOPIC_LABEL = "Coordinate Geometry of the Line"

TIERS = ["intro", "standard", "full"]
SUBTOPICS = [
    "slope_two_points",
    "slope_intercept_form",
    "equation_given_point_slope",
    "parallel_lines",
    "perpendicular_lines",
    "midpoint",
    "distance",
    "axis_intercepts",
]

_RANGE_BY_TIER = {"intro": (0, 6), "standard": (-8, 8), "full": (-10, 10)}


@dataclass
class Question:
    subtopic: str
    difficulty: str
    type: str
    prompt: str
    answer: str
    answer_type: str
    common_wrong_answers: list[dict[str, str]] = field(default_factory=list)
    # Seeds the drag-based interactive with THIS question's actual numbers —
    # without it, the diagram shows an unrelated example line, which is
    # more confusing than showing nothing at all.
    visualization: dict | None = None


def format_fraction(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def format_linear_equation(m: Fraction, c: Fraction) -> str:
    m_str = format_fraction(m)
    if c == 0:
        return f"y = {m_str}*x"
    sign = "+" if c > 0 else "-"
    return f"y = {m_str}*x {sign} {format_fraction(abs(c))}"


def rand_point(rng: random.Random, lo: int, hi: int, exclude_x: int | None = None) -> Point:
    while True:
        x = rng.randint(lo, hi)
        if exclude_x is not None and x == exclude_x:
            continue
        return Point(x, rng.randint(lo, hi))


def _points_on_line(m: Fraction, c: Fraction) -> tuple[list[float], list[float]]:
    """Two points on y = mx + c, for seeding the interactive with this
    question's actual line — the y-intercept itself (always exact), plus
    one more four units across."""
    return [0, float(c)], [4, float(m) * 4 + float(c)]


def _line_visualization(m: Fraction, c: Fraction, display_mode: str = "line") -> dict:
    point_a, point_b = _points_on_line(m, c)
    return {"pointA": point_a, "pointB": point_b, "displayMode": display_mode}


def _line_and_anchor_visualization(m: Fraction, c: Fraction, anchor: Point, mode: str) -> dict:
    return {**_line_visualization(m, c), "anchorPoint": [anchor.x, anchor.y], "mode": mode}


def rand_nonzero_slope(rng: random.Random, tier: str) -> Fraction:
    """A slope that's never 0 (perpendicular/parallel questions need a real line)."""
    numerator_range = {"intro": (1, 4), "standard": (1, 6), "full": (1, 8)}[tier]
    denominator_choices = {"intro": [1], "standard": [1, 1, 2], "full": [1, 2, 3, 4]}[tier]
    numerator = rng.randint(*numerator_range) * rng.choice([1, -1])
    denominator = rng.choice(denominator_choices)
    return Fraction(numerator, denominator)


def generate_slope_two_points(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    while True:
        p1 = rand_point(rng, lo, hi)
        p2 = rand_point(rng, lo, hi, exclude_x=p1.x)  # avoid a vertical (undefined-slope) line for now
        if p1 != p2:
            break
    # Fraction(p2.y - p1.y, p2.x - p1.x) directly, NOT Fraction(slope(p1, p2)) —
    # slope() does float division, and Fraction() on a float gives back that
    # float's exact (and usually hideous) binary representation, not the
    # simple rational a human would write.
    m = Fraction(p2.y - p1.y, p2.x - p1.x)
    return Question(
        subtopic="slope_two_points",
        difficulty=tier,
        type="numeric",
        answer_type="value",
        prompt=f"Find the slope of the line through the points ({p1.x}, {p1.y}) and ({p2.x}, {p2.y}).",
        answer=format_fraction(m),
        visualization={"pointA": [p1.x, p1.y], "pointB": [p2.x, p2.y], "displayMode": "segment-slope"},
    )


def generate_slope_intercept_form(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    a = rng.randint(1, 6) * rng.choice([1, -1]) if tier != "intro" else rng.randint(1, 4)
    c = rng.randint(lo, hi)
    # a*x + y = c rearranges to y = -a*x + c, so the y-intercept is (0, c)
    # regardless of a's sign — keeping the y coefficient at 1 keeps that exact.
    equation = f"{a}x + y = {c}"
    return Question(
        subtopic="slope_intercept_form",
        difficulty=tier,
        type="numeric",
        answer_type="point",
        prompt=(
            f"The line {equation} can be rearranged into the form y = mx + c. "
            "What is its y-intercept, written as a coordinate point?"
        ),
        answer=f"(0, {c})",
    )


def generate_equation_given_point_slope(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    m = rand_nonzero_slope(rng, tier)
    p = rand_point(rng, lo, hi)
    c = Fraction(p.y) - m * Fraction(p.x)
    return Question(
        subtopic="equation_given_point_slope",
        difficulty=tier,
        type="numeric",
        answer_type="equation",
        prompt=(
            f"A line has slope {format_fraction(m)} and passes through the point ({p.x}, {p.y}). "
            "Find the equation of the line in the form y = mx + c."
        ),
        answer=format_linear_equation(m, c),
    )


def generate_parallel_lines(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    m = rand_nonzero_slope(rng, tier)
    c1 = rng.randint(lo, hi)
    while True:
        r = rand_point(rng, lo, hi)
        c2 = Fraction(r.y) - m * Fraction(r.x)
        if c2 != c1:  # r must not already be on line k, or "line n" would just be line k again
            break
    common_wrong = [
        {"answer": format_linear_equation(m, Fraction(c1)), "misconception": "reused_original_intercept"}
    ]
    return Question(
        subtopic="parallel_lines",
        difficulty=tier,
        type="numeric",
        answer_type="equation",
        prompt=(
            f"Line k has equation {format_linear_equation(m, Fraction(c1))}. Line n is parallel to k and "
            f"passes through the point ({r.x}, {r.y}). Find the equation of line n."
        ),
        answer=format_linear_equation(m, c2),
        common_wrong_answers=common_wrong,
        visualization=_line_and_anchor_visualization(m, Fraction(c1), r, "parallel"),
    )


def generate_perpendicular_lines(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    m1 = rand_nonzero_slope(rng, tier)
    while abs(m1) == 1:  # at |m|=1, -1/m and m*-1 coincide, so the "wrong" answer wouldn't be wrong
        m1 = rand_nonzero_slope(rng, tier)
    c1 = rng.randint(lo, hi)
    r = rand_point(rng, lo, hi)
    m2 = perpendicular_slope(m1)
    assert m2 is not None
    c2 = Fraction(r.y) - m2 * Fraction(r.x)

    # The seed misconception: m * -1 instead of -1/m, applied through the same point.
    wrong_m = -m1
    wrong_c = Fraction(r.y) - wrong_m * Fraction(r.x)

    return Question(
        subtopic="perpendicular_lines",
        difficulty=tier,
        type="numeric",
        answer_type="equation",
        prompt=(
            f"Line k has equation {format_linear_equation(m1, Fraction(c1))}. Line n is perpendicular to k "
            f"and passes through the point ({r.x}, {r.y}). Find the equation of line n."
        ),
        answer=format_linear_equation(m2, c2),
        common_wrong_answers=[
            {"answer": format_linear_equation(wrong_m, wrong_c), "misconception": "mx_negative_one"}
        ],
        visualization=_line_and_anchor_visualization(m1, Fraction(c1), r, "perpendicular"),
    )


def generate_midpoint(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    p = rand_point(rng, lo, hi)
    q = rand_point(rng, lo, hi)
    mx = Fraction(p.x + q.x, 2)
    my = Fraction(p.y + q.y, 2)
    return Question(
        subtopic="midpoint",
        difficulty=tier,
        type="numeric",
        answer_type="point",
        prompt=f"Find the midpoint of the line segment joining ({p.x}, {p.y}) and ({q.x}, {q.y}).",
        answer=f"({format_fraction(mx)}, {format_fraction(my)})",
        visualization={"pointA": [p.x, p.y], "pointB": [q.x, q.y], "displayMode": "segment-midpoint"},
    )


_PYTHAGOREAN_OFFSETS = [(3, 4), (4, 3), (6, 8), (8, 6), (5, 12), (12, 5)]


def generate_distance(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    p = rand_point(rng, lo, hi)
    if tier == "intro":
        dx, dy = rng.choice(_PYTHAGOREAN_OFFSETS)
        q = Point(p.x + dx * rng.choice([1, -1]), p.y + dy * rng.choice([1, -1]))
    else:
        q = rand_point(rng, lo, hi)
        if q == p:
            q = Point(q.x + 1, q.y)
    dx, dy = q.x - p.x, q.y - p.y
    answer = str(sympy_sqrt(dx**2 + dy**2))
    return Question(
        subtopic="distance",
        difficulty=tier,
        type="numeric",
        answer_type="value",
        prompt=f"Find the distance between the points ({p.x}, {p.y}) and ({q.x}, {q.y}).",
        answer=answer,
        visualization={"pointA": [p.x, p.y], "pointB": [q.x, q.y], "displayMode": "segment-distance"},
    )


def generate_axis_intercepts(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    m = rand_nonzero_slope(rng, tier)
    c = 0
    while c == 0:  # c=0 makes the x-intercept trivially (0, 0), same as the y-intercept — not a real exercise
        c = rng.randint(lo, hi)
    x_intercept = -Fraction(c) / m
    return Question(
        subtopic="axis_intercepts",
        difficulty=tier,
        type="numeric",
        answer_type="point",
        prompt=f"Line k has equation {format_linear_equation(m, Fraction(c))}. Find where k crosses the x-axis.",
        answer=f"({format_fraction(x_intercept)}, 0)",
        visualization=_line_visualization(m, Fraction(c), display_mode="line-intercept"),
    )


_GENERATORS = {
    "slope_two_points": generate_slope_two_points,
    "slope_intercept_form": generate_slope_intercept_form,
    "equation_given_point_slope": generate_equation_given_point_slope,
    "parallel_lines": generate_parallel_lines,
    "perpendicular_lines": generate_perpendicular_lines,
    "midpoint": generate_midpoint,
    "distance": generate_distance,
    "axis_intercepts": generate_axis_intercepts,
}


def generate(subtopic: str, tier: str, rng: random.Random) -> Question:
    """Generate one fresh question instance for live serving."""
    if subtopic not in _GENERATORS:
        raise ValueError(f"Unknown subtopic '{subtopic}'. Expected one of {SUBTOPICS}.")
    if tier not in TIERS:
        raise ValueError(f"Unknown difficulty tier '{tier}'. Expected one of {TIERS}.")
    return _GENERATORS[subtopic](rng, tier)
