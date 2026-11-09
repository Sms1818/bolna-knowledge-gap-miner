import pytest

from app.api.routes.gap_analysis import (
    calculate_priority_score,
    check_knowledge_base,
    classify_answer,
)


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("", "unanswered"),
        (None, "unanswered"),
        ("I don't know.", "unanswered"),
        ("I'm not sure about that.", "unanswered"),
        ("Let me check that for you.", "partial"),
        ("I can help you with that.", "answered"),
        ("Your order will arrive in 5–7 business days.", "answered"),
        (
            "I don't know the exact date, but your order has shipped.",
            "partial",
        ),
        ("I think your package is on the way.", "partial"),
        ("Yes", "partial"),
    ],
)
def test_classify_answer(answer, expected):
    assert classify_answer(answer) == expected


@pytest.mark.parametrize(
    ("recurrence_count", "category", "expected"),
    [
        (1, "potential_kb_gap", 40.0),
        (2, "potential_kb_gap", 55.0),
        (3, "potential_kb_gap", 70.0),
        (1, "kb_retrieval_or_agent_gap", 30.0),
        (2, "kb_retrieval_or_agent_gap", 45.0),
        (6, "potential_kb_gap", 100.0),
        (10, "kb_retrieval_or_agent_gap", 100.0),
        (0, "potential_kb_gap", 25.0),
        (-1, "potential_kb_gap", 25.0),
        (2, "unknown_category", 30.0),
    ],
)
def test_calculate_priority_score(recurrence_count, category, expected):
    assert calculate_priority_score(recurrence_count, category) == expected


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Can I return a product after 30 days?", False),
        ("How can I track my order?", True),
        (
            "Can I change my delivery address after placing an order?",
            False,
        ),
    ],
)
def test_check_knowledge_base(question, expected):
    assert check_knowledge_base(question) is expected
