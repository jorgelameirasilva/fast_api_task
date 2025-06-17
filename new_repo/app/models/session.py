"""Pydantic models for session management"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from app.models.chat import ChatMessage


class Session(BaseModel):
    """Session model for storing conversation state"""

    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    messages: list[ChatMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    context: dict[str, Any] = Field(default_factory=dict, description="Session context")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    is_active: bool = Field(default=True, description="Whether session is active")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session"""

    user_id: str = Field(..., description="User identifier")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Initial session context"
    )


class SessionResponse(BaseModel):
    """Response model for session operations"""

    session: Session = Field(..., description="Session data")
    message: str = Field(default="Success", description="Response message")
