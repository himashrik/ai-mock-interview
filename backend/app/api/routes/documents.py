import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut, JDAnalysis, JDTextRequest, ResumeAnalysis
from app.services import document_processor
from app.services.authz import get_owned_document
from app.services.resume_jd_analyzer import analyze_jd, analyze_resume
from app.services.vector_store import index_document

router = APIRouter(tags=["documents"])


def _process_and_store(db: Session, document: Document) -> None:
    try:
        n_chunks = index_document(
            db,
            user_id=document.user_id,
            document_id=document.id,
            document_type=document.type,
            raw_text=document.raw_text,
        )
        document.status = "ready" if n_chunks > 0 else "failed"
        if n_chunks == 0:
            document.error_message = "Document produced no indexable content."
    except Exception as e:  # noqa: BLE001 - convert any pipeline failure into a stored status
        document.status = "failed"
        document.error_message = f"Indexing failed: {e}"
    db.commit()


@router.post("/resumes", response_model=DocumentOut)
async def upload_resume(
    file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    data, kind = await document_processor.validate_and_read_upload(file)
    try:
        text = document_processor.extract_text(data, kind)
    except document_processor.DocumentProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    document = Document(user_id=current_user.id, type="resume", filename=file.filename, raw_text=text, status="processing")
    db.add(document)
    db.commit()
    db.refresh(document)

    _process_and_store(db, document)
    return document


@router.get("/resumes", response_model=list[DocumentOut])
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.execute(
            select(Document)
            .where(Document.user_id == current_user.id, Document.type == "resume")
            .order_by(Document.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/resumes/{resume_id}", response_model=DocumentOut)
def get_resume(resume_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_owned_document(db, user_id=current_user.id, document_id=resume_id)


@router.get("/resumes/{resume_id}/analysis", response_model=ResumeAnalysis)
def get_resume_analysis(
    resume_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    doc = get_owned_document(db, user_id=current_user.id, document_id=resume_id)
    if doc.status != "ready":
        raise HTTPException(status_code=409, detail=f"Resume is not ready for analysis (status={doc.status}).")
    return analyze_resume(db, user_id=current_user.id, document_id=resume_id)


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = get_owned_document(db, user_id=current_user.id, document_id=resume_id)
    db.delete(doc)
    db.commit()
    return None


@router.post("/job-descriptions/upload", response_model=DocumentOut)
async def upload_jd_file(
    file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    data, kind = await document_processor.validate_and_read_upload(file)
    try:
        text = document_processor.extract_text(data, kind)
    except document_processor.DocumentProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    document = Document(
        user_id=current_user.id, type="jd", filename=file.filename, raw_text=text, status="processing"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _process_and_store(db, document)
    return document


@router.post("/job-descriptions/text", response_model=DocumentOut)
def paste_jd_text(
    payload: JDTextRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="JD text must not be empty.")

    document = Document(
        user_id=current_user.id, type="jd", filename=payload.title, raw_text=text, status="processing"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _process_and_store(db, document)
    return document


@router.get("/job-descriptions", response_model=list[DocumentOut])
def list_job_descriptions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.execute(
            select(Document)
            .where(Document.user_id == current_user.id, Document.type == "jd")
            .order_by(Document.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/job-descriptions/{jd_id}", response_model=DocumentOut)
def get_jd(jd_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_owned_document(db, user_id=current_user.id, document_id=jd_id)


@router.get("/job-descriptions/{jd_id}/analysis", response_model=JDAnalysis)
def get_jd_analysis(jd_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = get_owned_document(db, user_id=current_user.id, document_id=jd_id)
    if doc.status != "ready":
        raise HTTPException(status_code=409, detail=f"JD is not ready for analysis (status={doc.status}).")
    return analyze_jd(db, user_id=current_user.id, document_id=jd_id)
