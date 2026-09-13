import uuid
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

InterviewType = Literal["hr", "technical", "aptitude", "behavioral", "gd", "mixed"]
ExperienceLevel = Literal["fresher", "junior", "mid", "senior"]
Difficulty = Literal["easy", "medium", "hard"]
Mode = Literal["resume", "general"]


class InterviewCreateRequest(BaseModel):
    type: InterviewType
    target_role: str = Field(min_length=1, max_length=255)
    experience_level: ExperienceLevel
    difficulty: Difficulty
    mode: Mode
    num_questions: int = Field(default=8, ge=1, le=30)
    resume_id: Optional[uuid.UUID] = None
    jd_id: Optional[uuid.UUID] = None


class InterviewOut(BaseModel):
    id: uuid.UUID
    type: str
    target_role: str
    experience_level: str
    difficulty: str
    mode: str
    num_questions: int
    status: str
    overall_score: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    id: uuid.UUID
    index: int
    category: str
    text: str
    difficulty: str
    source: str

    model_config = ConfigDict(from_attributes=True)


class AnswerSubmitRequest(BaseModel):
    question_id: uuid.UUID
    text: str = Field(min_length=1, max_length=8000)


class FeedbackOut(BaseModel):
    score: float
    correctness: float
    relevance: float
    technical_accuracy: float
    completeness: float
    communication: float
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    sample_answer: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportOut(BaseModel):
    overall_score: float
    category_scores: dict
    strongest_areas: list[str]
    weakest_areas: list[str]
    common_mistakes: list[str]
    study_plan: list[str]
    tips: list[str]
    next_difficulty: str
    resume_alignment_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PerformanceHistoryItem(BaseModel):
    interview_id: uuid.UUID
    type: str
    target_role: str
    overall_score: Optional[float]
    completed_at: Optional[datetime]
