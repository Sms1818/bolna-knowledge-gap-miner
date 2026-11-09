import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class GapAnalysisJob(Base):
    __tablename__ = "gap_analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    questions: Mapped[list["ConversationQuestion"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ConversationQuestion(Base):
    __tablename__ = "conversation_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gap_analysis_jobs.id", ondelete="CASCADE")
    )
    conversation_id: Mapped[str] = mapped_column(String(100), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_status: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    job: Mapped["GapAnalysisJob"] = relationship(back_populates="questions")


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    evidence: Mapped[list["GapEvidence"]] = relationship(
        back_populates="gap", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["KnowledgeSuggestion"]] = relationship(
        back_populates="gap", cascade="all, delete-orphan"
    )


class GapEvidence(Base):
    __tablename__ = "gap_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_gaps.id", ondelete="CASCADE")
    )
    conversation_id: Mapped[str] = mapped_column(String(100), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_snippet: Mapped[str] = mapped_column(Text)

    gap: Mapped["KnowledgeGap"] = relationship(back_populates="evidence")


class KnowledgeSuggestion(Base):
    __tablename__ = "knowledge_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_gaps.id", ondelete="CASCADE")
    )
    suggested_content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending_review")
    reviewer_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    gap: Mapped["KnowledgeGap"] = relationship(back_populates="suggestions")
