import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    id: uuid.UUID
    type: str
    filename: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeAnalysis(BaseModel):
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []
    achievements: list[str] = []
    missing_information: list[str] = []
    potential_interview_topics: list[str] = []


class JDAnalysis(BaseModel):
    target_role: str = ""
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience_requirement: str = ""
    responsibilities: list[str] = []
    technologies: list[str] = []
    important_keywords: list[str] = []
    expected_competencies: list[str] = []


class JDTextRequest(BaseModel):
    text: str
    title: str = "Pasted Job Description"


class AtsAnalyzeRequest(BaseModel):
    resume_id: uuid.UUID
    jd_id: uuid.UUID


class AtsReportOut(BaseModel):
    id: uuid.UUID
    score: float
    matching_keywords: list[str]
    missing_keywords: list[str]
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
