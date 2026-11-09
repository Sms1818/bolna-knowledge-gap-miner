import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GapEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: str
    question_text: str
    answer_text: str | None
    evidence_snippet: str


class KnowledgeGapDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: str
    title: str
    description: str
    category: str
    recurrence_count: int
    priority_score: float
    status: str
    created_at: datetime
    evidence: list[GapEvidenceResponse]
