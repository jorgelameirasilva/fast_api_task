from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SessionMessage(BaseModel):
    """Single message document in sessions collection"""

    id: str = Field(alias="_id")
    user_id: str
    session_id: str
    message: dict  # Contains role and content
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionMessageCreate(BaseModel):
    """Schema for creating a new message"""

    user_id: str
    session_id: str
    message: dict
