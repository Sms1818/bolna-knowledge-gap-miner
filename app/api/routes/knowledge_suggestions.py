from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import KnowledgeGap, KnowledgeSuggestion
from app.schemas.knowledge_suggestion import (
    KnowledgeSuggestionCreate,
    KnowledgeSuggestionResponse,
)
from app.schemas.knowledge_suggestion_review import (
    KnowledgeSuggestionReviewRequest,
)

router = APIRouter(
    prefix="/v1/knowledge-gaps",
    tags=["Knowledge Suggestions"],
)


@router.post(
    "/{gap_id}/suggestions",
    response_model=KnowledgeSuggestionResponse,
    status_code=201,
)
async def create_knowledge_suggestion(
    gap_id: UUID,
    request: KnowledgeSuggestionCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeGap).where(KnowledgeGap.id == gap_id)
    )
    gap = result.scalar_one_or_none()

    if gap is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge gap not found",
        )

    suggestion = KnowledgeSuggestion(
        gap_id=gap.id,
        suggested_content=request.suggested_content,
        status="pending_review",
    )

    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    return suggestion


review_router = APIRouter(
    prefix="/v1/knowledge-suggestions",
    tags=["Knowledge Suggestions"],
)


@review_router.get(
    "",
    response_model=list[KnowledgeSuggestionResponse],
)
async def list_knowledge_suggestions(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeSuggestion).order_by(
            KnowledgeSuggestion.created_at.desc()
        )
    )

    return result.scalars().all()


@review_router.patch(
    "/{suggestion_id}",
    response_model=KnowledgeSuggestionResponse,
)
async def review_knowledge_suggestion(
    suggestion_id: UUID,
    request: KnowledgeSuggestionReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeSuggestion).where(
            KnowledgeSuggestion.id == suggestion_id
        )
    )
    suggestion = result.scalar_one_or_none()

    if suggestion is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge suggestion not found",
        )

    suggestion.status = request.status

    if request.suggested_content is not None:
        suggestion.suggested_content = request.suggested_content

    suggestion.reviewer_feedback = request.reviewer_feedback

    await db.commit()
    await db.refresh(suggestion)

    return suggestion
