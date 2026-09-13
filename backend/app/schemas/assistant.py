import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssistantMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
