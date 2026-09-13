from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantMessageOut
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/messages", response_model=list[AssistantMessageOut])
def get_messages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return assistant_service.get_history(db, user_id=current_user.id)


@router.post("/messages", response_model=AssistantMessageOut)
def post_message(
    payload: AssistantChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return assistant_service.send_message(db, user_id=current_user.id, message=payload.message)
