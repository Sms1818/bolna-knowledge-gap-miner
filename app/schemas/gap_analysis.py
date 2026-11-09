from uuid import UUID

from pydantic import BaseModel, Field


class ConversationInput(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=3)
    answer: str | None = None


class GapAnalysisRequest(BaseModel):
    conversations: list[ConversationInput] = Field(
        default_factory=list,
        max_length=500,
    )


class GapAnalysisResponse(BaseModel):
    job_id: UUID
    agent_id: str
    status: str
    total_conversations: int
