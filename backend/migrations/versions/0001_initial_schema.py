"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.core.config import settings

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = settings.embedding_dim


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False, server_default=""),
        sa.Column("parsed_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(16), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("chunk_metadata", sa.JSON, nullable=False, server_default="{}"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])
    # ivfflat index for fast approximate cosine-distance search; requires ANALYZE after bulk loads.
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_cosine ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "ats_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jd_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("matching_keywords", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("missing_keywords", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("strengths", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("weaknesses", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("suggestions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ats_reports_user_id", "ats_reports", ["user_id"])

    op.create_table(
        "interviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("jd_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("target_role", sa.String(255), nullable=False),
        sa.Column("experience_level", sa.String(32), nullable=False),
        sa.Column("difficulty", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("num_questions", sa.Integer, nullable=False, server_default="8"),
        sa.Column("status", sa.String(16), nullable=False, server_default="in_progress"),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_interviews_user_id", "interviews", ["user_id"])

    op.create_table(
        "questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("index", sa.Integer, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("grounding_chunk_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_questions_interview_id", "questions", ["interview_id"])

    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_answers_interview_id", "answers", ["interview_id"])
    op.create_index("ix_answers_user_id", "answers", ["user_id"])

    op.create_table(
        "feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("answer_id", UUID(as_uuid=True), sa.ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("correctness", sa.Float, nullable=False),
        sa.Column("relevance", sa.Float, nullable=False),
        sa.Column("technical_accuracy", sa.Float, nullable=False),
        sa.Column("completeness", sa.Float, nullable=False),
        sa.Column("communication", sa.Float, nullable=False),
        sa.Column("strengths", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("weaknesses", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("suggestions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("sample_answer", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("category_scores", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("strongest_areas", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("weakest_areas", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("common_mistakes", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("study_plan", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("tips", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("next_difficulty", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("resume_alignment_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("feedback")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("interviews")
    op.drop_table("ats_reports")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_cosine")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("users")
