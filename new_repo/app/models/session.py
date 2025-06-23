"""Pydantic models for session management"""

from datetime import datetime
from typing import Any, Optional
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


class ChatSession(BaseModel):
    """Extended session model for chat conversations with Cosmos DB support"""

    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    partition_key: str = Field(..., description="Partition key for Cosmos DB")
    title: Optional[str] = Field(None, description="Session title")
    messages: list[ChatMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    context: dict[str, Any] = Field(default_factory=dict, description="Session context")
    max_messages: int = Field(default=50, description="Maximum messages to keep")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    is_active: bool = Field(default=True, description="Whether session is active")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionSummary(BaseModel):
    """Summary model for session listings"""

    id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(None, description="Session title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages in session")
    is_active: bool = Field(default=True, description="Whether session is active")


class SessionSearchRequest(BaseModel):
    """Request model for searching sessions"""

    user_id: Optional[str] = Field(None, description="Filter by user ID")
    query: Optional[str] = Field(None, description="Search query for title and content")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    start_date: Optional[datetime] = Field(
        None, description="Filter by creation date (after)"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter by creation date (before)"
    )
    limit: int = Field(default=20, description="Maximum results to return")
    offset: int = Field(default=0, description="Number of results to skip")


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
