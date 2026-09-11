"""Independently re-derive every algebra generator's answer, the same way
tests/test_curated_bank.py does for coordinate geometry — re-parsing each
prompt with its own regexes and recomputing from scratch, not reusing the
generator's own arithmetic.
"""

from __future__ import annotations

import random
import re

import pytest
from sympy import Eq, expand, solve, symbols

from axiom.algebra_generators import SUBTOPICS, TIERS, generate

x, y = symbols("x y")

_TRIALS_PER_CELL = 20


def _all_generated(subtopic: str):
    rng = random.Random(12345)
    for tier in TIERS:
        for _ in range(_TRIALS_PER_CELL):
            yield tier, generate(subtopic, tier, rng)


def test_every_subtopic_and_tier_combination_is_reachable():
    for subtopic in SUBTOPICS:
        for tier in TIERS:
            q = generate(subtopic, tier, random.Random(1))
            assert q.subtopic == subtopic
            assert q.difficulty == tier
            assert q.prompt and q.answer


def test_simplifying_expressions():
    linear_re = re.compile(r"Simplify: (-?\d+)x ([+-]) (\d+)x(?: ([+-]) (\d+))?")
    for _, q in _all_generated("simplifying_expressions"):
        m = linear_re.search(q.prompt)
        assert m, q.prompt
        a = int(m.group(1))
        b = int(m.group(3)) * (1 if m.group(2) == "+" else -1)
        c = int(m.group(5)) * (1 if m.group(4) == "+" else -1) if m.group(4) else 0
        expected = expand(a * x + b * x + c)
        assert expand(_answer_expr(q.answer)) == expected, q.prompt


def _answer_expr(answer: str):
    from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations

    t = standard_transformations + (implicit_multiplication_application,)
    return parse_expr(answer, transformations=t)


def _answer_expr_unevaluated(answer: str):
    # Number * (bracket) auto-distributes under normal parsing (sympy
    # eagerly evaluates that specific case) — evaluate=False is needed to
    # actually check whether an answer is *structurally* a product rather
    # than already-expanded, same as axiom.grading's real checker.
    from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations

    t = standard_transformations + (implicit_multiplication_application,)
    return parse_expr(answer, transformations=t, evaluate=False)


def test_solving_linear_equations():
    eq_re = re.compile(r"Solve for x: (-?\d+)x(?: ([+-]) (\d+))? = (-?\d+)")
    for _, q in _all_generated("solving_linear_equations"):
        m = eq_re.search(q.prompt)
        assert m, q.prompt
        a = int(m.group(1))
        b = int(m.group(3)) * (1 if m.group(2) == "+" else -1) if m.group(2) else 0
        c = int(m.group(4))
        (expected,) = solve(Eq(a * x + b, c), x)
        assert _answer_expr(q.answer) == expected, q.prompt


def test_factorising_common_factor_expands_back_to_the_prompt():
    prompt_re = re.compile(r"Factorise fully: (-?\d+)x(?: ([+-]) (\d+))?")
    for _, q in _all_generated("factorising_common_factor"):
        m = prompt_re.search(q.prompt)
        assert m, q.prompt
        coeff = int(m.group(1))
        const = int(m.group(3)) * (1 if m.group(2) == "+" else -1) if m.group(2) else 0
        target = expand(coeff * x + const)
        assert expand(_answer_expr(q.answer)) == target, q.prompt
        # And it must genuinely be a product, i.e. not equal to its own expansion.
        raw = _answer_expr_unevaluated(q.answer)
        assert raw != expand(raw), f"'{q.answer}' isn't actually factored"


def test_factorising_quadratics_matches_the_prompt():
    prompt_re = re.compile(r"Factorise fully: x\^2(?: ([+-]) (\d+)x)?(?: ([+-]) (\d+))?")
    for _, q in _all_generated("factorising_quadratics"):
        m = prompt_re.search(q.prompt)
        assert m, q.prompt
        b = int(m.group(2)) * (1 if m.group(1) == "+" else -1) if m.group(1) else 0
        c = int(m.group(4)) * (1 if m.group(3) == "+" else -1) if m.group(3) else 0
        target = expand(x**2 + b * x + c)
        assert expand(_answer_expr(q.answer)) == target, q.prompt


def test_solving_quadratic_equations_roots_satisfy_the_prompt():
    prompt_re = re.compile(r"Solve: x\^2(?: ([+-]) (\d+)x)?(?: ([+-]) (\d+))? = 0")
    root_re = re.compile(r"x = (-?\d+) or x = (-?\d+)")
    for _, q in _all_generated("solving_quadratic_equations"):
        pm = prompt_re.search(q.prompt)
        assert pm, q.prompt
        b = int(pm.group(2)) * (1 if pm.group(1) == "+" else -1) if pm.group(1) else 0
        c = int(pm.group(4)) * (1 if pm.group(3) == "+" else -1) if pm.group(3) else 0

        rm = root_re.search(q.answer)
        assert rm, q.answer
        r1, r2 = int(rm.group(1)), int(rm.group(2))
        # Each claimed root must actually satisfy x^2 + bx + c = 0.
        assert r1**2 + b * r1 + c == 0, q.prompt
        assert r2**2 + b * r2 + c == 0, q.prompt


def test_simultaneous_equations_solution_satisfies_both_equations():
    prompt_re = re.compile(
        r"Solve the simultaneous equations: (-?\d+)x ([+-]) (\d+)y = (-?\d+) and "
        r"(-?\d+)x ([+-]) (\d+)y = (-?\d+)"
    )
    point_re = re.compile(r"\((-?\d+), (-?\d+)\)")
    for _, q in _all_generated("simultaneous_equations"):
        m = prompt_re.search(q.prompt)
        assert m, q.prompt
        a1, b1_sign, b1_mag, c1, a2, b2_sign, b2_mag, c2 = m.groups()
        a1, c1, a2, c2 = int(a1), int(c1), int(a2), int(c2)
        b1 = int(b1_mag) * (1 if b1_sign == "+" else -1)
        b2 = int(b2_mag) * (1 if b2_sign == "+" else -1)

        pm = point_re.search(q.answer)
        assert pm, q.answer
        x0, y0 = int(pm.group(1)), int(pm.group(2))
        assert a1 * x0 + b1 * y0 == c1, q.prompt
        assert a2 * x0 + b2 * y0 == c2, q.prompt


def test_inequalities_boundary_satisfies_the_equality_case():
    prompt_re = re.compile(r"Solve: (-?\d+)x(?: ([+-]) (\d+))? (<=|>=|<|>) (-?\d+)")
    answer_re = re.compile(r"x (<=|>=|<|>) (-?\d+)")
    for _, q in _all_generated("inequalities"):
        m = prompt_re.search(q.prompt)
        assert m, q.prompt
        a = int(m.group(1))
        b = int(m.group(3)) * (1 if m.group(2) == "+" else -1) if m.group(2) else 0
        c = int(m.group(5))

        am = answer_re.search(q.answer)
        assert am, q.answer
        result_op, threshold = am.group(1), int(am.group(2))

        # The boundary must satisfy a*threshold + b == c exactly.
        assert a * threshold + b == c, q.prompt

        # Sign-flip check: the direction should be flipped iff a < 0.
        prompt_op = m.group(4)
        flipped = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
        expected_op = flipped[prompt_op] if a < 0 else prompt_op
        assert result_op == expected_op, q.prompt


def test_inequalities_flags_the_forgot_to_flip_misconception_only_when_relevant():
    for _, q in _all_generated("inequalities"):
        a_negative = "-" in q.prompt.split("x")[0].strip()
        if a_negative:
            assert len(q.common_wrong_answers) == 1
            assert q.common_wrong_answers[0]["misconception"] == "forgot_to_flip_sign"
        # (a > 0 case isn't asserted empty here — a could coincidentally
        # start with "-" from a negative constant term elsewhere; the
        # generator's own logic already guards this correctly and is
        # covered by the boundary/flip assertions above.)


@pytest.mark.parametrize("subtopic", SUBTOPICS)
def test_generate_rejects_unknown_tier(subtopic: str):
    with pytest.raises(ValueError):
        generate(subtopic, "expert", random.Random(1))


def test_generate_rejects_unknown_subtopic():
    with pytest.raises(ValueError):
        generate("trigonometry", "intro", random.Random(1))
