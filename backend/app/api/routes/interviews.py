import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.document import Document
from app.models.interview import Answer, Feedback, Interview, Question, Report
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmitRequest,
    FeedbackOut,
    InterviewCreateRequest,
    InterviewOut,
    PerformanceHistoryItem,
    QuestionOut,
    ReportOut,
)
from app.services.authz import get_owned_document, get_owned_interview
from app.services.interview_engine import generate_next_question
from app.services.evaluator import evaluate_answer
from app.services.report_generator import generate_report

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewOut)
def create_interview(
    payload: InterviewCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    resume_doc: Document | None = None
    jd_doc: Document | None = None

    if payload.mode == "resume":
        if not payload.resume_id:
            raise HTTPException(status_code=400, detail="resume_id is required when mode='resume'.")
        resume_doc = get_owned_document(db, user_id=current_user.id, document_id=payload.resume_id)
        if resume_doc.status != "ready":
            raise HTTPException(status_code=409, detail="Selected resume has not finished processing.")
        if payload.jd_id:
            jd_doc = get_owned_document(db, user_id=current_user.id, document_id=payload.jd_id)
            if jd_doc.status != "ready":
                raise HTTPException(status_code=409, detail="Selected job description has not finished processing.")

    interview = Interview(
        user_id=current_user.id,
        resume_document_id=resume_doc.id if resume_doc else None,
        jd_document_id=jd_doc.id if jd_doc else None,
        type=payload.type,
        target_role=payload.target_role,
        experience_level=payload.experience_level,
        difficulty=payload.difficulty,
        mode=payload.mode,
        num_questions=payload.num_questions,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


@router.get("", response_model=list[InterviewOut])
def list_interviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.execute(
            select(Interview).where(Interview.user_id == current_user.id).order_by(Interview.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_owned_interview(db, user_id=current_user.id, interview_id=interview_id)


@router.post("/{interview_id}/next-question", response_model=Optional[QuestionOut])
def next_question(interview_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_owned_interview(db, user_id=current_user.id, interview_id=interview_id)
    if interview.status == "completed":
        raise HTTPException(status_code=409, detail="Interview is already completed.")

    asked_count = db.query(Question).filter(Question.interview_id == interview.id).count()

    # If the most recently asked question hasn't been answered yet, return it instead of generating a new one.
    if asked_count > 0:
        last_question = (
            db.execute(
                select(Question).where(Question.interview_id == interview.id).order_by(Question.index.desc())
            )
            .scalars()
            .first()
        )
        answered = db.query(Answer).filter(Answer.question_id == last_question.id).first()
        if answered is None:
            return last_question

    if asked_count >= interview.num_questions:
        return None  # frontend should call /complete

    return generate_next_question(db, interview, asked_count)


@router.post("/{interview_id}/answers", response_model=FeedbackOut)
def submit_answer(
    interview_id: uuid.UUID,
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = get_owned_interview(db, user_id=current_user.id, interview_id=interview_id)

    question = db.get(Question, payload.question_id)
    if question is None or question.interview_id != interview.id:
        raise HTTPException(status_code=404, detail="Question not found in this interview.")

    existing = db.query(Answer).filter(Answer.question_id == question.id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="This question has already been answered.")

    answer = Answer(
        question_id=question.id, interview_id=interview.id, user_id=current_user.id, text=payload.text
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    feedback = evaluate_answer(db, interview, question, answer)
    return feedback


@router.post("/{interview_id}/complete", response_model=ReportOut)
def complete_interview(interview_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_owned_interview(db, user_id=current_user.id, interview_id=interview_id)
    if interview.status == "completed":
        existing_report = db.query(Report).filter(Report.interview_id == interview.id).first()
        if existing_report:
            return existing_report

    answered = db.query(Answer).filter(Answer.interview_id == interview.id).count()
    if answered == 0:
        raise HTTPException(status_code=400, detail="Cannot complete an interview with no answered questions.")

    return generate_report(db, interview)


@router.get("/{interview_id}/report", response_model=ReportOut)
def get_report(interview_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_owned_interview(db, user_id=current_user.id, interview_id=interview_id)
    report = db.query(Report).filter(Report.interview_id == interview.id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not generated yet. Complete the interview first.")
    return report
