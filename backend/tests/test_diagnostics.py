from axiom.diagnostics import build_diagnostic_offer, get_worked_example, next_subtopic_miss_count
from axiom.topics import TOPICS


def test_correct_answer_resets_the_miss_count():
    assert next_subtopic_miss_count(current=3, correct=True) == 0


def test_wrong_answer_increments_the_miss_count():
    assert next_subtopic_miss_count(current=1, correct=False) == 2


def test_offer_is_neutral_before_two_misses():
    offer = build_diagnostic_offer("perpendicular_lines", miss_count=1)
    assert offer == {"available": True, "prerequisiteNodeId": "perpendicular_lines", "nudge": False}


def test_offer_becomes_a_nudge_at_two_misses():
    offer = build_diagnostic_offer("perpendicular_lines", miss_count=2)
    assert offer["nudge"] is True


def test_offer_stays_a_nudge_beyond_two_misses():
    offer = build_diagnostic_offer("perpendicular_lines", miss_count=5)
    assert offer["nudge"] is True


def test_every_subtopic_in_every_topic_has_a_worked_example():
    for topic in TOPICS.values():
        for subtopic in topic.SUBTOPICS:
            example = get_worked_example(subtopic)
            assert example is not None, subtopic
            assert example["title"] and example["explanation"] and example["example"]


def test_perpendicular_worked_example_names_the_negative_reciprocal():
    example = get_worked_example("perpendicular_lines")
    assert "-1/m" in example["explanation"] or "-1/m" in example["title"]


def test_unknown_subtopic_returns_none():
    assert get_worked_example("calculus") is None
