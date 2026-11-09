import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import (
    GapAnalysisJob,
    ConversationQuestion,
    KnowledgeGap,
    GapEvidence,
)
from app.schemas.gap_analysis import (
    GapAnalysisRequest,
    GapAnalysisResponse,
)

router = APIRouter(
    prefix="/v1/agents",
    tags=["Gap Analysis"],
)

MOCK_KNOWLEDGE_BASE = [
    "Customers can return eligible products within 30 days "
    "of delivery. Items must be unused and in original packaging.",
    "Standard shipping takes 5 to 7 business days.",
    "Customers can track orders using the tracking link "
    "sent by email after shipment.",
]

UNANSWERED_PHRASES = {
    "i don't know",
    "i do not know",
    "i am not sure",
    "i'm not sure",
    "let me check",
    "i cannot help",
    "i can't help",
    "no information",
    "not available",
}

STOP_WORDS = {
    "what", "when", "where", "which", "who", "why", "how",
    "can", "could", "would", "should", "does", "did", "do",
    "is", "are", "was", "were", "the", "a", "an", "i",
    "my", "me", "we", "our", "you", "your", "it", "this",
    "that", "after", "before", "for", "from", "with", "and",
    "or", "to", "of", "in", "on", "at", "be", "been",
}


def normalize_question(question: str) -> str:
    """Normalize question text for deterministic grouping."""
    question = question.lower().strip()
    question = re.sub(r"[^a-z0-9\s]", "", question)
    question = re.sub(r"\s+", " ", question)
    return question


def meaningful_words(text: str) -> set[str]:
    words = set(normalize_question(text).split())

    return {
        word.rstrip("s")
        for word in words
        if len(word) > 3 and word not in STOP_WORDS
    }


def classify_answer(answer: str | None) -> str:
    """
    Deterministic classification of an agent response.
    """
    if not answer or not answer.strip():
        return "unanswered"

    normalized = " ".join(answer.lower().strip().split())
    words = normalized.split()

    check_phrases = (
        "let me check",
        "i will check",
        "i'll check",
        "i can check",
        "let me confirm",
        "i will confirm",
        "i'll confirm",
    )

    if any(phrase in normalized for phrase in check_phrases):
        return "partial"

    unanswered_match = any(
        phrase in normalized for phrase in UNANSWERED_PHRASES
    )

    if unanswered_match:
        if " but " in normalized or " however " in normalized:
            return "partial"
        return "unanswered"

    partial_phrases = (
        "let me check",
        "i will check",
        "i'll check",
        "i can check",
        "let me confirm",
        "i will confirm",
        "i'll confirm",
        "not sure",
        "maybe",
        "possibly",
        "i think",
    )

    if any(phrase in normalized for phrase in partial_phrases):
        return "partial"

    if len(words) < 4:
        return "partial"

    return "answered"


def calculate_priority_score(
    recurrence_count: int,
    category: str,
) -> float:
    """
    Deterministic priority score based on unique conversation recurrence
    and the type of knowledge gap.
    """
    recurrence_score = max(0, recurrence_count) * 15.0

    category_bonus = {
        "potential_kb_gap": 25.0,
        "kb_retrieval_or_agent_gap": 15.0,
    }.get(category, 0.0)

    return min(100.0, recurrence_score + category_bonus)


def check_knowledge_base(question: str) -> bool:
    """
    Conservative mock KB coverage check.
    Detects explicit temporal mismatches before keyword matching.
    """
    normalized_question = normalize_question(question)

    # The mock KB only supports returns within 30 days.
    # A question about returns after 30 days is not covered.
    if (
        "return" in normalized_question
        and "after 30 days" in normalized_question
    ):
        return False

    question_words = meaningful_words(question)

    if not question_words:
        return False

    for article in MOCK_KNOWLEDGE_BASE:
        article_words = meaningful_words(article)

        overlap = question_words.intersection(article_words)

        coverage_ratio = len(overlap) / len(question_words)

        if coverage_ratio >= 0.60:
            return True

    return False

@router.post(
    "/{agent_id}/gap-analysis",
    response_model=GapAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_gap_analysis(
    agent_id: str,
    request: GapAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    job = GapAnalysisJob(
        agent_id=agent_id,
        status="processing",
        total_conversations=len(request.conversations),
    )

    db.add(job)
    await db.flush()

    grouped_gaps = {}

    for conversation in request.conversations:
        answer_status = classify_answer(conversation.answer)

        question_record = ConversationQuestion(
            job_id=job.id,
            conversation_id=conversation.conversation_id,
            question_text=conversation.question,
            answer_text=conversation.answer,
            answer_status=answer_status,
            confidence=(
                0.90 if answer_status == "unanswered" else 0.75
            ),
        )

        db.add(question_record)

        if answer_status == "answered":
            continue

        normalized_question = normalize_question(
            conversation.question
        )

        if normalized_question not in grouped_gaps:
            grouped_gaps[normalized_question] = {
                "question": conversation.question,
                "evidence": [],
                "kb_covered": check_knowledge_base(
                    conversation.question
                ),
            }

        grouped_gaps[normalized_question]["evidence"].append(
            {
                "conversation_id": conversation.conversation_id,
                "question": conversation.question,
                "answer": conversation.answer,
            }
        )

    # Load existing gaps for this agent.
    existing_gaps_result = await db.execute(
        select(KnowledgeGap).where(
            KnowledgeGap.agent_id == agent_id
        )
    )

    existing_gaps = existing_gaps_result.scalars().all()

    # Map normalized gap titles to existing gap records.
    existing_gap_map = {}

    for existing_gap in existing_gaps:
        normalized_title = normalize_question(
            existing_gap.title
        )

        existing_gap_map[normalized_title] = existing_gap

    for normalized_question, group in grouped_gaps.items():
        kb_covered = group["kb_covered"]

        category = (
            "potential_kb_gap"
            if not kb_covered
            else "kb_retrieval_or_agent_gap"
        )

        gap = existing_gap_map.get(normalized_question)

        if gap is None:
            gap = KnowledgeGap(
                agent_id=agent_id,
                title=group["question"][:255],
                description=(
                    "Repeated customer question requiring review. "
                    f"Mock knowledge base coverage: "
                    f"{'detected' if kb_covered else 'not detected'}."
                ),
                category=category,
                recurrence_count=0,
                priority_score=0.0,
                status="open",
            )

            db.add(gap)
            await db.flush()

            existing_gap_map[normalized_question] = gap

        # Get existing evidence for this gap.
        evidence_result = await db.execute(
            select(GapEvidence).where(
                GapEvidence.gap_id == gap.id
            )
        )

        existing_evidence = evidence_result.scalars().all()

        existing_conversation_ids = {
            evidence.conversation_id
            for evidence in existing_evidence
        }

        # Add only evidence from previously unseen conversations.
        for evidence in group["evidence"]:
            conversation_id = evidence["conversation_id"]

            if conversation_id in existing_conversation_ids:
                continue

            db.add(
                GapEvidence(
                    gap_id=gap.id,
                    conversation_id=conversation_id,
                    question_text=evidence["question"],
                    answer_text=evidence["answer"],
                    evidence_snippet=(
                        f"Customer asked: {evidence['question']}. "
                        f"Agent response: "
                        f"{evidence['answer'] or 'No response recorded'}."
                    ),
                )
            )

            existing_conversation_ids.add(conversation_id)

        # Recurrence is based on unique conversation evidence.
        gap.recurrence_count = len(existing_conversation_ids)

        # Deterministic priority based on recurrence and gap category.
        gap.priority_score = calculate_priority_score(
            gap.recurrence_count,
            category,
        )

        gap.category = category

        gap.description = (
            "Repeated customer question requiring review. "
            f"Mock knowledge base coverage: "
            f"{'detected' if kb_covered else 'not detected'}."
        )

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)

    return GapAnalysisResponse(
        job_id=job.id,
        agent_id=job.agent_id,
        status=job.status,
        total_conversations=job.total_conversations,
    )
