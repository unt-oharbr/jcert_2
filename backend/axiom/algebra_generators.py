"""Parametric question generators for Algebra: Solving Equations & Factorising.

Same approach as axiom/question_generators.py: every answer is computed
from exact Fraction/sympy arithmetic, and a fresh instance is generated
live on every request rather than pulled from a fixed bank.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from fractions import Fraction

TOPIC_ID = "algebra_equations"
TOPIC_LABEL = "Algebra: Solving Equations & Factorising"

TIERS = ["intro", "standard", "full"]
SUBTOPICS = [
    "simplifying_expressions",
    "solving_linear_equations",
    "factorising_common_factor",
    "factorising_quadratics",
    "solving_quadratic_equations",
    "simultaneous_equations",
    "inequalities",
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


def format_fraction(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        n = rng.randint(lo, hi)
        if n != 0:
            return n


def signed_term(coefficient: int, symbol: str = "") -> str:
    """`+ 5x` / `- 5x`, for joining onto a preceding term."""
    sign = "+" if coefficient >= 0 else "-"
    return f"{sign} {abs(coefficient)}{symbol}"


def maybe_signed_term(coefficient: int, symbol: str = "") -> str:
    """Like signed_term, but vanishes for a zero coefficient — a real
    exam prints "x^2 - 9", not "x^2 + 0x - 9"."""
    return signed_term(coefficient, symbol) if coefficient != 0 else ""


def join_terms(*terms: str) -> str:
    return " ".join(t for t in terms if t)


def factor_str(root: int) -> str:
    """`(x - root)`, simplified for root == 0."""
    if root == 0:
        return "x"
    if root > 0:
        return f"(x - {root})"
    return f"(x + {-root})"


def generate_simplifying_expressions(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    a = nonzero_int(rng, lo, hi)
    b = nonzero_int(rng, lo, hi)
    c = rng.randint(lo, hi)

    prompt = f"Simplify: {join_terms(f'{a}x', signed_term(b, 'x'), maybe_signed_term(c))}"

    combined = a + b
    if combined == 0:
        answer = format_fraction(Fraction(c)) if c != 0 else "0"
    elif combined == 1:
        answer = join_terms("x", maybe_signed_term(c)) or "x"
    elif combined == -1:
        answer = join_terms("-x", maybe_signed_term(c)) or "-x"
    else:
        answer = join_terms(f"{combined}x", maybe_signed_term(c))

    return Question(
        subtopic="simplifying_expressions",
        difficulty=tier,
        type="numeric",
        answer_type="value",
        prompt=prompt,
        answer=answer,
    )


def generate_solving_linear_equations(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    x_solution = rng.randint(lo, hi)
    a = nonzero_int(rng, lo, hi)
    b = rng.randint(lo, hi)
    c = a * x_solution + b

    prompt = f"Solve for x: {join_terms(f'{a}x', maybe_signed_term(b))} = {c}"

    return Question(
        subtopic="solving_linear_equations",
        difficulty=tier,
        type="numeric",
        answer_type="value",
        prompt=prompt,
        answer=format_fraction(Fraction(x_solution)),
    )


def generate_factorising_common_factor(rng: random.Random, tier: str) -> Question:
    k = rng.randint(2, 6)
    while True:
        p = nonzero_int(rng, -6, 6)
        q = nonzero_int(rng, -6, 6)
        if math.gcd(abs(p), abs(q)) == 1:
            break

    expanded_coeff = k * p
    expanded_const = k * q
    prompt = f"Factorise fully: {join_terms(f'{expanded_coeff}x', signed_term(expanded_const))}"
    answer = f"{k}({join_terms(f'{p}x', signed_term(q))})"

    return Question(
        subtopic="factorising_common_factor",
        difficulty=tier,
        type="numeric",
        answer_type="factored_expression",
        prompt=prompt,
        answer=answer,
    )


def _random_root_pair(rng: random.Random, tier: str) -> tuple[int, int]:
    _, hi = _RANGE_BY_TIER[tier]
    bound = min(hi, 8) or 6  # `or` is safe here: min(hi, 8) is never 0 for any real tier, but stay defensive
    while True:
        r1 = rng.randint(-bound, bound)
        r2 = rng.randint(-bound, bound)
        if not (r1 == 0 and r2 == 0):  # x^2 = 0 is a degenerate, trivial "factorisation"
            return r1, r2


def generate_factorising_quadratics(rng: random.Random, tier: str) -> Question:
    r1, r2 = _random_root_pair(rng, tier)
    b_coeff = -(r1 + r2)
    c_const = r1 * r2
    prompt = f"Factorise fully: {join_terms('x^2', maybe_signed_term(b_coeff, 'x'), maybe_signed_term(c_const))}"
    answer = f"{factor_str(r1)}{factor_str(r2)}"

    return Question(
        subtopic="factorising_quadratics",
        difficulty=tier,
        type="numeric",
        answer_type="factored_expression",
        prompt=prompt,
        answer=answer,
    )


def generate_solving_quadratic_equations(rng: random.Random, tier: str) -> Question:
    r1, r2 = _random_root_pair(rng, tier)
    b_coeff = -(r1 + r2)
    c_const = r1 * r2
    prompt = f"Solve: {join_terms('x^2', maybe_signed_term(b_coeff, 'x'), maybe_signed_term(c_const))} = 0"
    answer = f"x = {r1} or x = {r2}"

    return Question(
        subtopic="solving_quadratic_equations",
        difficulty=tier,
        type="numeric",
        answer_type="root_set",
        prompt=prompt,
        answer=answer,
    )


def generate_simultaneous_equations(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    x0 = rng.randint(lo, hi)
    y0 = rng.randint(lo, hi)

    a1 = nonzero_int(rng, lo, hi)
    b1 = nonzero_int(rng, lo, hi)
    c1 = a1 * x0 + b1 * y0

    while True:
        a2 = nonzero_int(rng, lo, hi)
        b2 = nonzero_int(rng, lo, hi)
        if a1 * b2 - a2 * b1 != 0:  # non-singular -> a unique solution
            break
    c2 = a2 * x0 + b2 * y0

    prompt = (
        f"Solve the simultaneous equations: {join_terms(f'{a1}x', signed_term(b1, 'y'))} = {c1} "
        f"and {join_terms(f'{a2}x', signed_term(b2, 'y'))} = {c2}. Give your answer as (x, y)."
    )

    return Question(
        subtopic="simultaneous_equations",
        difficulty=tier,
        type="numeric",
        answer_type="point",
        prompt=prompt,
        answer=f"({x0}, {y0})",
    )


_OPERATORS = ["<", ">", "<=", ">="]
_FLIPPED = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}


def generate_inequalities(rng: random.Random, tier: str) -> Question:
    lo, hi = _RANGE_BY_TIER[tier]
    x_threshold = rng.randint(lo, hi)
    a = nonzero_int(rng, lo, hi)
    b = rng.randint(lo, hi)
    c = a * x_threshold + b
    operator = rng.choice(_OPERATORS)

    prompt = f"Solve: {join_terms(f'{a}x', maybe_signed_term(b))} {operator} {c}"

    result_operator = _FLIPPED[operator] if a < 0 else operator
    answer = f"x {result_operator} {x_threshold}"

    common_wrong: list[dict[str, str]] = []
    if a < 0:
        # The seed-style misconception here: forgetting that dividing by a
        # negative flips the inequality, so the direction is left unchanged.
        common_wrong.append({"answer": f"x {operator} {x_threshold}", "misconception": "forgot_to_flip_sign"})

    return Question(
        subtopic="inequalities",
        difficulty=tier,
        type="numeric",
        answer_type="inequality",
        prompt=prompt,
        answer=answer,
        common_wrong_answers=common_wrong,
    )


_GENERATORS = {
    "simplifying_expressions": generate_simplifying_expressions,
    "solving_linear_equations": generate_solving_linear_equations,
    "factorising_common_factor": generate_factorising_common_factor,
    "factorising_quadratics": generate_factorising_quadratics,
    "solving_quadratic_equations": generate_solving_quadratic_equations,
    "simultaneous_equations": generate_simultaneous_equations,
    "inequalities": generate_inequalities,
}


def generate(subtopic: str, tier: str, rng: random.Random) -> Question:
    if subtopic not in _GENERATORS:
        raise ValueError(f"Unknown subtopic '{subtopic}'. Expected one of {SUBTOPICS}.")
    if tier not in TIERS:
        raise ValueError(f"Unknown difficulty tier '{tier}'. Expected one of {TIERS}.")
    return _GENERATORS[subtopic](rng, tier)
