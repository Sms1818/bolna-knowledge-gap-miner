from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeSuggestionReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    suggested_content: str | None = Field(default=None, min_length=1)
    reviewer_feedback: str | None = None
