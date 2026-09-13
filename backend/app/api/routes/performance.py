from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.interview import Interview
from app.models.user import User
from app.schemas.interview import PerformanceHistoryItem

router = APIRouter(prefix="/me", tags=["performance"])


@router.get("/performance-history", response_model=list[PerformanceHistoryItem])
def performance_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interviews = (
        db.execute(
            select(Interview)
            .where(Interview.user_id == current_user.id, Interview.status == "completed")
            .order_by(Interview.completed_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        PerformanceHistoryItem(
            interview_id=i.id, type=i.type, target_role=i.target_role,
            overall_score=i.overall_score, completed_at=i.completed_at,
        )
        for i in interviews
    ]
