import pytest
from sqlalchemy import select

from app.models.entities import (
    ConversationQuestion,
    GapAnalysisJob,
    GapEvidence,
    KnowledgeGap,
)


async def test_gap_analysis_creates_job_and_persists_gaps(
    client,
    test_db,
):
    payload = {
        "conversations": [
            {
                "conversation_id": "integration-return-001",
                "question": "Can I return a product after 30 days?",
                "answer": "I don't know.",
            },
            {
                "conversation_id": "integration-return-002",
                "question": "Can I return a product after 30 days?",
                "answer": "I'm not sure about that.",
            },
        ]
    }

    response = await client.post(
        "/v1/agents/integration-agent/gap-analysis",
        json=payload,
    )

    assert response.status_code == 202

    body = response.json()

    assert body["agent_id"] == "integration-agent"
    assert body["status"] == "completed"
    assert body["total_conversations"] == 2
    assert body["job_id"]

    job_result = await test_db.execute(
        select(GapAnalysisJob).where(
            GapAnalysisJob.agent_id == "integration-agent"
        )
    )

    job = job_result.scalar_one()

    assert str(job.id) == body["job_id"]
    assert job.status == "completed"

    questions_result = await test_db.execute(
        select(ConversationQuestion).where(
            ConversationQuestion.job_id == job.id
        )
    )

    questions = questions_result.scalars().all()

    assert len(questions) == 2
    assert all(
        question.answer_status == "unanswered"
        for question in questions
    )

    gaps_result = await test_db.execute(
        select(KnowledgeGap).where(
            KnowledgeGap.agent_id == "integration-agent"
        )
    )

    gaps = gaps_result.scalars().all()

    assert len(gaps) == 1

    gap = gaps[0]

    assert gap.recurrence_count == 2
    assert gap.category == "potential_kb_gap"
    assert gap.priority_score == 55.0

    evidence_result = await test_db.execute(
        select(GapEvidence).where(
            GapEvidence.gap_id == gap.id
        )
    )

    evidence = evidence_result.scalars().all()

    assert len(evidence) == 2

    assert {
        item.conversation_id for item in evidence
    } == {
        "integration-return-001",
        "integration-return-002",
    }


async def test_repeated_conversation_does_not_duplicate_evidence(
    client,
    test_db,
):
    payload = {
        "conversations": [
            {
                "conversation_id": "dedup-return-001",
                "question": "Can I return a product after 30 days?",
                "answer": "I don't know.",
            },
        ]
    }

    # First API request
    first_response = await client.post(
        "/v1/agents/dedup-agent/gap-analysis",
        json=payload,
    )

    assert first_response.status_code == 202

    # Second API request with the exact same conversation
    second_response = await client.post(
        "/v1/agents/dedup-agent/gap-analysis",
        json=payload,
    )

    assert second_response.status_code == 202

    # Verify only one knowledge gap exists
    gaps_result = await test_db.execute(
        select(KnowledgeGap).where(
            KnowledgeGap.agent_id == "dedup-agent"
        )
    )

    gaps = gaps_result.scalars().all()

    assert len(gaps) == 1

    gap = gaps[0]

    # Recurrence must remain 1
    assert gap.recurrence_count == 1

    # Priority must remain 40
    assert gap.priority_score == 40.0

    # Evidence must not be duplicated
    evidence_result = await test_db.execute(
        select(GapEvidence).where(
            GapEvidence.gap_id == gap.id
        )
    )

    evidence = evidence_result.scalars().all()

    assert len(evidence) == 1
    assert evidence[0].conversation_id == "dedup-return-001"


@pytest.mark.parametrize(
    "conversation",
    [
        {
            "conversation_id": "",
            "question": "Can I return my product?",
            "answer": "I don't know.",
        },
        {
            "conversation_id": "invalid-question-001",
            "question": "Hi",
            "answer": "I don't know.",
        },
    ],
)
async def test_gap_analysis_rejects_invalid_conversations(
    client,
    conversation,
):
    response = await client.post(
        "/v1/agents/validation-agent/gap-analysis",
        json={"conversations": [conversation]},
    )

    assert response.status_code == 422


async def test_list_knowledge_gaps_returns_persisted_gap(
    client,
):
    payload = {
        "conversations": [
            {
                "conversation_id": "list-gap-001",
                "question": "Can I return a product after 30 days?",
                "answer": "I don't know.",
            },
        ]
    }

    create_response = await client.post(
        "/v1/agents/list-agent/gap-analysis",
        json=payload,
    )

    assert create_response.status_code == 202

    response = await client.get(
        "/v1/agents/list-agent/knowledge-gaps"
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["title"] == (
        "Can I return a product after 30 days?"
    )
    assert body[0]["recurrence_count"] == 1
    assert body[0]["priority_score"] == 40.0


async def test_get_nonexistent_knowledge_gap_returns_404(
    client,
):
    response = await client.get(
        "/v1/knowledge-gaps/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


async def test_list_knowledge_gaps_returns_empty_list_for_new_agent(
    client,
):
    response = await client.get(
        "/v1/agents/agent-with-no-gaps/knowledge-gaps"
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_knowledge_gap_with_invalid_uuid_returns_422(
    client,
):
    response = await client.get(
        "/v1/knowledge-gaps/not-a-valid-uuid"
    )

    assert response.status_code == 422


async def test_get_knowledge_gap_detail_includes_evidence(
    client,
):
    payload = {
        "conversations": [
            {
                "conversation_id": "detail-test-001",
                "question": "Can I return a product after 30 days?",
                "answer": "I don't know.",
            },
            {
                "conversation_id": "detail-test-002",
                "question": "Can I return a product after 30 days?",
                "answer": "I'm not sure about that.",
            },
        ]
    }

    create_response = await client.post(
        "/v1/agents/detail-agent/gap-analysis",
        json=payload,
    )

    assert create_response.status_code == 202

    gaps_response = await client.get(
        "/v1/agents/detail-agent/knowledge-gaps"
    )

    assert gaps_response.status_code == 200

    gaps = gaps_response.json()
    assert len(gaps) == 1

    gap_id = gaps[0]["id"]

    detail_response = await client.get(
        f"/v1/knowledge-gaps/{gap_id}"
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["id"] == gap_id
    assert detail["agent_id"] == "detail-agent"
    assert detail["title"] == (
        "Can I return a product after 30 days?"
    )
    assert detail["category"] == "potential_kb_gap"
    assert detail["recurrence_count"] == 2
    assert detail["priority_score"] == 55.0
    assert detail["status"] == "open"

    evidence = detail["evidence"]

    assert len(evidence) == 2

    assert {
        item["conversation_id"] for item in evidence
    } == {
        "detail-test-001",
        "detail-test-002",
    }

    assert all(
        item["question_text"]
        == "Can I return a product after 30 days?"
        for item in evidence
    )


async def test_create_knowledge_suggestion(client):
    payload = {
        "conversations": [
            {
                "conversation_id": "suggestion-test-001",
                "question": "Can I return a product after 30 days?",
                "answer": "I don't know.",
            },
            {
                "conversation_id": "suggestion-test-002",
                "question": "Can I return a product after 30 days?",
                "answer": "I'm not sure about that.",
            },
        ]
    }

    create_gap_response = await client.post(
        "/v1/agents/suggestion-agent/gap-analysis",
        json=payload,
    )

    assert create_gap_response.status_code == 202

    gaps_response = await client.get(
        "/v1/agents/suggestion-agent/knowledge-gaps"
    )

    gap_id = gaps_response.json()[0]["id"]

    suggestion_response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": (
                "Products can be returned within 30 days "
                "of purchase, subject to the return policy."
            )
        },
    )

    assert suggestion_response.status_code == 201

    suggestion = suggestion_response.json()

    assert suggestion["gap_id"] == gap_id
    assert suggestion["status"] == "pending_review"
    assert suggestion["reviewer_feedback"] is None
    assert "30 days" in suggestion["suggested_content"]


async def test_review_knowledge_suggestion_approved(client):
    payload = {
        "conversations": [
            {
                "conversation_id": "review-approved-001",
                "question": "Does the company offer free shipping?",
                "answer": "I don't know.",
            },
            {
                "conversation_id": "review-approved-002",
                "question": "Does the company offer free shipping?",
                "answer": "I'm not sure.",
            },
        ]
    }

    await client.post(
        "/v1/agents/review-agent/gap-analysis",
        json=payload,
    )

    gaps_response = await client.get(
        "/v1/agents/review-agent/knowledge-gaps"
    )

    gap_id = gaps_response.json()[0]["id"]

    suggestion_response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": "Free shipping is available."
        },
    )

    suggestion_id = suggestion_response.json()["id"]

    review_response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "approved",
            "reviewer_feedback": "Verified and approved.",
        },
    )

    assert review_response.status_code == 200

    reviewed_suggestion = review_response.json()

    assert reviewed_suggestion["status"] == "approved"
    assert (
        reviewed_suggestion["reviewer_feedback"]
        == "Verified and approved."
    )
    assert (
        reviewed_suggestion["suggested_content"]
        == "Free shipping is available."
    )


async def test_review_knowledge_suggestion_rejected(client):
    payload = {
        "conversations": [
            {
                "conversation_id": "review-rejected-001",
                "question": "Is express delivery available?",
                "answer": "I don't know.",
            },
            {
                "conversation_id": "review-rejected-002",
                "question": "Is express delivery available?",
                "answer": "I'm not sure.",
            },
        ]
    }

    await client.post(
        "/v1/agents/rejected-agent/gap-analysis",
        json=payload,
    )

    gaps_response = await client.get(
        "/v1/agents/rejected-agent/knowledge-gaps"
    )

    gap_id = gaps_response.json()[0]["id"]

    suggestion_response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": "Express delivery is always free."
        },
    )

    suggestion_id = suggestion_response.json()["id"]

    review_response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "rejected",
            "reviewer_feedback": "This information is unverified.",
        },
    )

    assert review_response.status_code == 200

    reviewed_suggestion = review_response.json()

    assert reviewed_suggestion["status"] == "rejected"
    assert (
        reviewed_suggestion["reviewer_feedback"]
        == "This information is unverified."
    )


async def test_review_nonexistent_knowledge_suggestion_returns_404(
    client,
):
    suggestion_id = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "approved",
            "reviewer_feedback": "Approved.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Knowledge suggestion not found"
    )


async def test_review_knowledge_suggestion_invalid_status_returns_422(
    client,
):
    suggestion_id = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "pending_review",
        },
    )

    assert response.status_code == 422


async def test_create_suggestion_for_nonexistent_gap_returns_404(
    client,
):
    gap_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": "A sample knowledge article."
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge gap not found"


async def test_create_suggestion_with_invalid_gap_id_returns_422(
    client,
):
    response = await client.post(
        "/v1/knowledge-gaps/invalid-uuid/suggestions",
        json={
            "suggested_content": "A sample knowledge article."
        },
    )

    assert response.status_code == 422


async def test_create_suggestion_without_content_returns_422(
    client,
):
    gap_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={},
    )

    assert response.status_code == 422


async def test_create_suggestion_with_empty_content_returns_422(
    client,
):
    gap_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={"suggested_content": ""},
    )

    assert response.status_code == 422


async def test_create_suggestion_with_whitespace_content_returns_422(
    client,
):
    gap_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={"suggested_content": "   "},
    )

    assert response.status_code == 422


async def test_review_suggestion_with_empty_content_returns_422(
    client,
):
    suggestion_id = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "approved",
            "suggested_content": "",
        },
    )

    assert response.status_code == 422


async def test_review_suggestion_with_invalid_uuid_returns_422(
    client,
):
    response = await client.patch(
        "/v1/knowledge-suggestions/not-a-uuid",
        json={
            "status": "approved",
        },
    )

    assert response.status_code == 422


async def _create_test_gap(client, agent_id="test-suggestion-agent"):
    response = await client.post(
        f"/v1/agents/{agent_id}/gap-analysis",
        json={
            "conversations": [
                {
                    "conversation_id": f"{agent_id}-conversation",
                    "question": "Can I return a product after 30 days?",
                    "answer": "I don't know.",
                }
            ]
        },
    )

    assert response.status_code == 202

    gaps_response = await client.get(
        f"/v1/agents/{agent_id}/knowledge-gaps"
    )

    assert gaps_response.status_code == 200
    gaps = gaps_response.json()
    assert len(gaps) >= 1

    return gaps[0]["id"]


async def test_knowledge_gap_list_orders_by_priority(client):
    agent_id = "test-priority-ordering"

    response = await client.post(
        f"/v1/agents/{agent_id}/gap-analysis",
        json={
            "conversations": [
                {
                    "conversation_id": "priority-conversation-1",
                    "question": "Can I return a product after 30 days?",
                    "answer": "I don't know.",
                },
                {
                    "conversation_id": "priority-conversation-2",
                    "question": "Can I return a product after 30 days?",
                    "answer": "I don't know.",
                },
                {
                    "conversation_id": "priority-conversation-3",
                    "question": "How can I track my order?",
                    "answer": "I don't know.",
                },
            ]
        },
    )

    assert response.status_code == 202

    gaps_response = await client.get(
        f"/v1/agents/{agent_id}/knowledge-gaps"
    )

    assert gaps_response.status_code == 200

    gaps = gaps_response.json()
    assert len(gaps) == 2
    assert gaps[0]["priority_score"] >= gaps[1]["priority_score"]


async def test_gap_analysis_answered_conversation_creates_no_gap(client):
    agent_id = "test-answered-only"

    response = await client.post(
        f"/v1/agents/{agent_id}/gap-analysis",
        json={
            "conversations": [
                {
                    "conversation_id": "answered-conversation",
                    "question": "How can I track my order?",
                    "answer": (
                        "You can track your order using the tracking link "
                        "sent by email after shipment."
                    ),
                }
            ]
        },
    )

    assert response.status_code == 202

    gaps_response = await client.get(
        f"/v1/agents/{agent_id}/knowledge-gaps"
    )

    assert gaps_response.status_code == 200
    assert gaps_response.json() == []


async def test_review_suggestion_updates_content_and_feedback(client):
    gap_id = await _create_test_gap(client)

    create_response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": "Initial suggested knowledge content."
        },
    )

    assert create_response.status_code == 201

    suggestion_id = create_response.json()["id"]

    review_response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "approved",
            "suggested_content": "Updated approved knowledge content.",
            "reviewer_feedback": "Reviewed and approved.",
        },
    )

    assert review_response.status_code == 200

    data = review_response.json()

    assert data["status"] == "approved"
    assert data["suggested_content"] == (
        "Updated approved knowledge content."
    )
    assert data["reviewer_feedback"] == "Reviewed and approved."


async def test_review_suggestion_without_content_update(client):
    gap_id = await _create_test_gap(
        client,
        agent_id="test-review-no-content",
    )

    create_response = await client.post(
        f"/v1/knowledge-gaps/{gap_id}/suggestions",
        json={
            "suggested_content": "Preserve this original content."
        },
    )

    assert create_response.status_code == 201

    suggestion_id = create_response.json()["id"]

    review_response = await client.patch(
        f"/v1/knowledge-suggestions/{suggestion_id}",
        json={
            "status": "rejected",
            "reviewer_feedback": "Needs more detail.",
        },
    )

    assert review_response.status_code == 200

    data = review_response.json()

    assert data["status"] == "rejected"
    assert data["suggested_content"] == (
        "Preserve this original content."
    )
    assert data["reviewer_feedback"] == "Needs more detail."
