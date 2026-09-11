"""Registry of every topic's question-generator module.

Each topic module (axiom.question_generators, axiom.algebra_generators, ...)
exports the same shape: TOPIC_ID, TOPIC_LABEL, SUBTOPICS, TIERS, and a
generate(subtopic, tier, rng) function. This is the single lookup point
Lambda handlers use instead of hardcoding which topic exists.
"""

from __future__ import annotations

from axiom import algebra_generators, question_generators

TOPICS = {
    question_generators.TOPIC_ID: question_generators,
    algebra_generators.TOPIC_ID: algebra_generators,
}
