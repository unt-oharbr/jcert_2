from scripts.list_flags import _reproduce


def _flag(**overrides):
    base = {
        "questionId": "q1",
        "topicId": "algebra_equations",
        "subtopic": "solving_linear_equations",
        "difficulty": "standard",
        "seed": 999,
        "prompt": None,
        "canonicalAnswer": None,
    }
    return {**base, **overrides}


def test_reproduce_confirms_a_matching_flag():
    # Actually generate once first to know what seed 999 legitimately produces.
    import random

    from axiom.topics import TOPICS

    question = TOPICS["algebra_equations"].generate("solving_linear_equations", "standard", random.Random(999))

    result = _reproduce(_flag(prompt=question.prompt, canonicalAnswer=question.answer))

    assert "matches stored prompt/answer" in result
    assert question.prompt in result


def test_reproduce_flags_a_mismatch():
    result = _reproduce(_flag(prompt="this is not what seed 999 actually produces", canonicalAnswer="wrong"))

    assert "DIFFERS" in result


def test_reproduce_handles_a_missing_seed():
    result = _reproduce(_flag(seed=None))

    assert "no seed stored" in result


def test_reproduce_handles_an_unknown_topic():
    result = _reproduce(_flag(topicId="not_a_real_topic"))

    assert "unknown topicId" in result
