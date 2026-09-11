"""Coordinate geometry of the line: slope, parallel/perpendicular checks.

This module exists to encode the exact first-principles relationship behind
the seed misconception for this whole project: a perpendicular line's
gradient is the negative *reciprocal* of the original (``-1/m``), not the
original gradient with its sign flipped (``m * -1``). Rotating a line 90
degrees swaps its rise and run and flips one sign — that's where ``-1/m``
comes from, and it's why the two wrong-looking-similar formulas produce
different answers for every gradient except +-1.
"""

from __future__ import annotations

from dataclasses import dataclass

_TOLERANCE = 1e-9


@dataclass(frozen=True)
class Point:
    x: float
    y: float


def slope(a: Point, b: Point) -> float | None:
    """Gradient of the line through ``a`` and ``b``, or ``None`` if vertical."""
    if a.x == b.x:
        return None
    return (b.y - a.y) / (b.x - a.x)


def is_parallel(m1: float | None, m2: float | None) -> bool:
    """Two lines are parallel when their gradients match (both vertical counts)."""
    if m1 is None or m2 is None:
        return m1 is None and m2 is None
    return abs(m1 - m2) < _TOLERANCE


def is_perpendicular(m1: float | None, m2: float | None) -> bool:
    """Two lines are perpendicular when ``m1 * m2 == -1``, or one is vertical
    (``None``) and the other horizontal (``0``).
    """
    if m1 is None or m2 is None:
        other = m2 if m1 is None else m1
        return other == 0
    if m1 == 0 or m2 == 0:
        return False
    return abs(m1 * m2 + 1) < _TOLERANCE


def perpendicular_slope(m: float | None) -> float | None:
    """The gradient perpendicular to ``m``. Vertical (``None``) <-> horizontal (``0``)."""
    if m is None:
        return 0.0
    if m == 0:
        return None
    return -1 / m


def matches_mx_negative_one_misconception(m: float, submitted: float) -> bool:
    """True if ``submitted`` looks like the ``m * -1`` mistake rather than ``-1/m``.

    Used to tag *why* an answer is wrong, not just that it is — the app can
    then show the specific worked example that addresses this exact slip
    instead of a generic "perpendicular lines" explainer.
    """
    correct = perpendicular_slope(m)
    if correct is None:
        return False
    looks_like_sign_flip = abs(submitted - (-m)) < _TOLERANCE
    is_actually_wrong = abs(submitted - correct) >= _TOLERANCE
    return looks_like_sign_flip and is_actually_wrong
