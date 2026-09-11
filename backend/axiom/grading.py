"""Check a typed answer against a canonical one, by meaning rather than text.

`3.5` and `7/2` are the same answer; `y=2x-1` and `y = 2*x - 1` are the same
line. Comparing strings directly would mark a genuinely correct answer
wrong just because she formatted it differently — sympy compares the
underlying maths instead.
"""

from __future__ import annotations

import re

from sympy import expand, simplify
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


class UnparseableAnswer(ValueError):
    """Raised when a submitted answer can't be parsed as maths at all — a
    formatting problem, not a wrong answer, so callers can respond
    differently (e.g. "we couldn't read that" rather than "incorrect")."""


def _parse_value(text: str):
    try:
        return parse_expr(text, transformations=_TRANSFORMATIONS)
    except Exception as exc:  # sympy raises several different exception types
        raise UnparseableAnswer(f"Couldn't parse '{text}' as a value.") from exc


def _values_equal(a: str, b: str) -> bool:
    diff = simplify(_parse_value(a) - _parse_value(b))
    return diff == 0


def _parse_point(text: str) -> tuple:
    inner = text.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]
    parts = inner.split(",")
    if len(parts) != 2:
        raise UnparseableAnswer(f"Couldn't parse '{text}' as a coordinate point.")
    return tuple(_parse_value(p) for p in parts)


def _points_equal(a: str, b: str) -> bool:
    (ax, ay), (bx, by) = _parse_point(a), _parse_point(b)
    return simplify(ax - bx) == 0 and simplify(ay - by) == 0


def _parse_equation_rhs(text: str):
    """`y = 2*x - 1` (or her looser `y=2x-1`) -> the expression `2*x - 1`."""
    if "=" not in text:
        raise UnparseableAnswer(f"Couldn't parse '{text}' as an equation of a line.")
    _lhs, rhs = text.split("=", 1)
    return _parse_value(rhs.strip())


def _equations_equal(a: str, b: str) -> bool:
    diff = simplify(_parse_equation_rhs(a) - _parse_equation_rhs(b))
    return diff == 0


def _parse_unevaluated(text: str):
    """Like _parse_value, but without sympy's automatic simplification —
    `evaluate=True` (the default) eagerly distributes a *number* times a
    bracket during parsing (though not two symbolic brackets together), so
    `3*(2*x+3)` would otherwise become indistinguishable from `6*x+9`
    before this module ever got a look at it."""
    try:
        return parse_expr(text, transformations=_TRANSFORMATIONS, evaluate=False)
    except Exception as exc:
        raise UnparseableAnswer(f"Couldn't parse '{text}' as a value.") from exc


def _factored_expressions_equal(a: str, b: str) -> bool:
    """Same polynomial AND actually presented as a product, not the
    original expanded form handed back unchanged."""
    submitted_raw = _parse_unevaluated(a)
    if simplify(expand(submitted_raw) - expand(_parse_value(b))) != 0:
        return False
    return submitted_raw != expand(submitted_raw)


_ROOT_SET_SPLIT_RE = re.compile(r",|\bor\b", re.IGNORECASE)
_ROOT_SET_PREFIX_RE = re.compile(r"^\s*x\s*=\s*", re.IGNORECASE)


def _parse_root_set(text: str) -> set:
    values = set()
    for part in _ROOT_SET_SPLIT_RE.split(text):
        part = _ROOT_SET_PREFIX_RE.sub("", part.strip())
        if part:
            values.add(_parse_value(part))
    if not values:
        raise UnparseableAnswer(f"Couldn't parse '{text}' as a set of solutions.")
    return values


def _root_sets_equal(a: str, b: str) -> bool:
    return _parse_root_set(a) == _parse_root_set(b)


_INEQUALITY_RE = re.compile(r"x\s*(<=|>=|<|>)\s*(.+)")


def _parse_inequality(text: str) -> tuple[str, object]:
    match = _INEQUALITY_RE.search(text)
    if not match:
        raise UnparseableAnswer(f"Couldn't parse '{text}' as an inequality in x.")
    return match.group(1), _parse_value(match.group(2).strip())


def _inequalities_equal(a: str, b: str) -> bool:
    op_a, val_a = _parse_inequality(a)
    op_b, val_b = _parse_inequality(b)
    return op_a == op_b and simplify(val_a - val_b) == 0


_CHECKERS = {
    "value": _values_equal,
    "point": _points_equal,
    "equation": _equations_equal,
    "factored_expression": _factored_expressions_equal,
    "root_set": _root_sets_equal,
    "inequality": _inequalities_equal,
}


def check_answer(answer_type: str, submitted: str, canonical: str) -> bool:
    """True if `submitted` means the same thing as `canonical`.

    Raises UnparseableAnswer if `submitted` isn't parseable maths at all —
    that's a different situation from being wrong, and callers should
    handle it differently (e.g. ask her to check her formatting).
    """
    if answer_type not in _CHECKERS:
        raise ValueError(f"Unknown answer_type '{answer_type}'. Expected one of {list(_CHECKERS)}.")
    return _CHECKERS[answer_type](submitted, canonical)
