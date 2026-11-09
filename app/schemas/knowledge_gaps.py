from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    title: str
    description: str
    category: str
    recurrence_count: int
    priority_score: float
    status: str
    created_at: datetime
