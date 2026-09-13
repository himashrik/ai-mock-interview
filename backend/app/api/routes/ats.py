import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.document import AtsReport
from app.models.user import User
from app.schemas.document import AtsAnalyzeRequest, AtsReportOut
from app.services.ats_analyzer import AtsAnalysisUnavailable, run_ats_analysis
from app.services.authz import get_owned_document

router = APIRouter(prefix="/ats", tags=["ats"])


@router.post("/analyze", response_model=AtsReportOut)
def analyze(payload: AtsAnalyzeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resume = get_owned_document(db, user_id=current_user.id, document_id=payload.resume_id)
    jd = get_owned_document(db, user_id=current_user.id, document_id=payload.jd_id)

    if resume.type != "resume" or jd.type != "jd":
        raise HTTPException(status_code=400, detail="resume_id must reference a resume and jd_id a job description.")
    if resume.status != "ready" or jd.status != "ready":
        raise HTTPException(status_code=409, detail="Both documents must finish processing before ATS analysis.")

    try:
        result = run_ats_analysis(
            db, user_id=current_user.id, resume_document_id=resume.id, jd_document_id=jd.id
        )
    except AtsAnalysisUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    report = AtsReport(
        user_id=current_user.id,
        resume_document_id=resume.id,
        jd_document_id=jd.id,
        score=result.score,
        matching_keywords=result.matching_keywords,
        missing_keywords=result.missing_keywords,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        suggestions=result.suggestions,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=AtsReportOut)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.get(AtsReport, report_id)
    if report is None or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="ATS report not found.")
    return report
