import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GUID


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    jd_document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # hr|technical|aptitude|behavioral|gd|mixed
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_level: Mapped[str] = mapped_column(String(32), nullable=False)  # fresher|junior|mid|senior
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)  # easy|medium|hard
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # resume|general
    num_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")  # in_progress|completed
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # resume|jd|general|followup
    grounding_chunk_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("answers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    correctness: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    technical_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    communication: Mapped[float] = mapped_column(Float, nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sample_answer: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    strongest_areas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weakest_areas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    common_mistakes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    study_plan: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tips: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    next_difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    resume_alignment_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
