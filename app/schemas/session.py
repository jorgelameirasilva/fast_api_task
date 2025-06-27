from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from .chat import ChatMessage


class SessionMessage(BaseModel):
    """Message stored in session"""

    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """Session model for database storage"""

    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[SessionMessage] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionCreate(BaseModel):
    """Schema for creating a new session"""

    user_id: str


class SessionUpdate(BaseModel):
    """Schema for updating a session"""

    messages: List[SessionMessage]
    updated_at: datetime = Field(default_factory=datetime.utcnow)
