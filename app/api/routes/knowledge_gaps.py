from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import KnowledgeGap
from app.schemas.knowledge_gaps import KnowledgeGapResponse

router = APIRouter(
    prefix="/v1/agents",
    tags=["Knowledge Gaps"],
)


@router.get(
    "/{agent_id}/knowledge-gaps",
    response_model=list[KnowledgeGapResponse],
)
async def list_knowledge_gaps(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(KnowledgeGap)
        .where(KnowledgeGap.agent_id == agent_id)
        .order_by(KnowledgeGap.priority_score.desc())
    )

    result = await db.execute(query)

    return result.scalars().all()


from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import selectinload

from app.schemas.knowledge_gap_detail import KnowledgeGapDetailResponse


detail_router = APIRouter(
    prefix="/v1/knowledge-gaps",
    tags=["Knowledge Gap Details"],
)


@detail_router.get(
    "/{gap_id}",
    response_model=KnowledgeGapDetailResponse,
)
async def get_knowledge_gap_detail(
    gap_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(KnowledgeGap)
        .options(selectinload(KnowledgeGap.evidence))
        .where(KnowledgeGap.id == gap_id)
    )

    result = await db.execute(query)
    gap = result.scalar_one_or_none()

    if gap is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge gap not found",
        )

    return gap
