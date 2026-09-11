import random

import pytest

from axiom.question_generators import SUBTOPICS, TIERS, generate


@pytest.mark.parametrize("subtopic", SUBTOPICS)
@pytest.mark.parametrize("tier", TIERS)
def test_generate_produces_a_well_formed_question(subtopic: str, tier: str):
    q = generate(subtopic, tier, random.Random(1))
    assert q.subtopic == subtopic
    assert q.difficulty == tier
    assert q.prompt
    assert q.answer


def test_generate_gives_different_questions_on_different_seeds():
    # The whole point of live generation: she should never see the same
    # instance twice just because she asked for the same subtopic/tier.
    seen = {generate("perpendicular_lines", "standard", random.Random(seed)).prompt for seed in range(20)}
    assert len(seen) > 1


def test_generate_rejects_unknown_subtopic():
    with pytest.raises(ValueError):
        generate("calculus", "intro", random.Random(1))


def test_generate_rejects_unknown_tier():
    with pytest.raises(ValueError):
        generate("midpoint", "expert", random.Random(1))


VISUALIZED_SUBTOPICS = [
    "slope_two_points",
    "parallel_lines",
    "perpendicular_lines",
    "midpoint",
    "distance",
    "axis_intercepts",
]


@pytest.mark.parametrize("subtopic", VISUALIZED_SUBTOPICS)
@pytest.mark.parametrize("tier", TIERS)
def test_visualized_subtopics_always_include_visualization_data(subtopic: str, tier: str):
    q = generate(subtopic, tier, random.Random(7))
    assert q.visualization is not None
    assert "pointA" in q.visualization and "pointB" in q.visualization


@pytest.mark.parametrize("subtopic", [s for s in SUBTOPICS if s not in VISUALIZED_SUBTOPICS])
def test_non_visualized_subtopics_have_no_visualization_data(subtopic: str):
    q = generate(subtopic, "intro", random.Random(1))
    assert q.visualization is None


def test_slope_two_points_visualization_matches_the_prompt_points():
    for seed in range(20):
        q = generate("slope_two_points", "standard", random.Random(seed))
        p1, p2 = _points_in(q.prompt)
        assert q.visualization == {
            "pointA": [p1[0], p1[1]],
            "pointB": [p2[0], p2[1]],
            "displayMode": "segment-slope",
        }


@pytest.mark.parametrize("subtopic,mode", [("parallel_lines", "parallel"), ("perpendicular_lines", "perpendicular")])
def test_line_and_anchor_visualization_is_internally_consistent(subtopic: str, mode: str):
    import re
    from fractions import Fraction

    for seed in range(20):
        q = generate(subtopic, "standard", random.Random(seed))
        vis = q.visualization
        assert vis["mode"] == mode

        # pointA and pointB must actually lie on the same line (i.e. the
        # slope between them matches what a human would compute) — this
        # would catch, e.g., a units mix-up between pointA and pointB.
        (ax, ay), (bx, by) = vis["pointA"], vis["pointB"]
        assert bx != ax
        line_slope = (by - ay) / (bx - ax)

        # And that line must be the actual "line k" from the prompt text.
        m = re.search(r"y = (-?\d+(?:/\d+)?)\*x(?: ([+-]) (\d+(?:/\d+)?))?", q.prompt)
        prompt_slope = float(Fraction(m.group(1)))
        assert line_slope == pytest.approx(prompt_slope)

        # The anchor point must match the point named in the prompt.
        point_match = re.search(r"\((-?\d+), (-?\d+)\)", q.prompt)
        assert vis["anchorPoint"] == [int(point_match.group(1)), int(point_match.group(2))]


def _points_in(text: str):
    import re

    return [(int(x), int(y)) for x, y in re.findall(r"\((-?\d+),\s*(-?\d+)\)", text)]


def test_midpoint_visualization_matches_the_prompt_points():
    for seed in range(20):
        q = generate("midpoint", "standard", random.Random(seed))
        p1, p2 = _points_in(q.prompt)
        assert q.visualization == {
            "pointA": [p1[0], p1[1]],
            "pointB": [p2[0], p2[1]],
            "displayMode": "segment-midpoint",
        }


def test_distance_visualization_matches_the_prompt_points():
    for seed in range(20):
        q = generate("distance", "standard", random.Random(seed))
        p1, p2 = _points_in(q.prompt)
        assert q.visualization == {
            "pointA": [p1[0], p1[1]],
            "pointB": [p2[0], p2[1]],
            "displayMode": "segment-distance",
        }


def test_axis_intercepts_visualization_lies_on_the_prompt_line():
    import re
    from fractions import Fraction

    for seed in range(20):
        q = generate("axis_intercepts", "standard", random.Random(seed))
        vis = q.visualization
        assert vis["displayMode"] == "line-intercept"
        assert "anchorPoint" not in vis  # no second line here, just the one line and its intercept

        (ax, ay), (bx, by) = vis["pointA"], vis["pointB"]
        assert bx != ax
        line_slope = (by - ay) / (bx - ax)

        m = re.search(r"y = (-?\d+(?:/\d+)?)\*x(?: ([+-]) (\d+(?:/\d+)?))?", q.prompt)
        prompt_slope = float(Fraction(m.group(1)))
        assert line_slope == pytest.approx(prompt_slope)
