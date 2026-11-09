import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeSuggestionCreate(BaseModel):
    suggested_content: str = Field(min_length=1)
    @field_validator("suggested_content")
    @classmethod
    def validate_suggested_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Suggested content cannot be empty")
        return value



class KnowledgeSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gap_id: uuid.UUID
    suggested_content: str
    status: str
    reviewer_feedback: str | None
    created_at: datetime
