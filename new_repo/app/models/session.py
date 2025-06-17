"""Pydantic models for session management in Cosmos DB"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.chat import ChatMessage


class ChatSession(BaseModel):
    """Model for storing chat sessions in Cosmos DB"""

    # Cosmos DB document fields
    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier from auth claims")

    # Session metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    is_active: bool = Field(default=True, description="Whether session is active")

    # Chat data
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Conversation history"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Session context and overrides"
    )

    # Session settings
    title: Optional[str] = Field(
        None, description="Session title (generated from first message)"
    )
    max_messages: int = Field(
        default=50, description="Maximum messages to keep in history"
    )

    # Cosmos DB partition key
    partition_key: str = Field(..., description="Partition key for Cosmos DB (user_id)")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionSummary(BaseModel):
    """Lightweight session summary for listing user sessions"""

    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Session title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages in session")
    is_active: bool = Field(default=True, description="Whether session is active")


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session"""

    title: Optional[str] = Field(None, description="Optional session title")
    context: Dict[str, Any] = Field(default_factory=dict, description="Initial context")
    max_messages: int = Field(default=50, description="Maximum messages to keep")


class UpdateSessionRequest(BaseModel):
    """Request model for updating session metadata"""

    title: Optional[str] = Field(None, description="Updated session title")
    context: Optional[Dict[str, Any]] = Field(None, description="Updated context")
    is_active: Optional[bool] = Field(None, description="Updated active status")
    max_messages: Optional[int] = Field(None, description="Updated max messages limit")


class AddMessageRequest(BaseModel):
    """Request model for adding a message to a session"""

    message: ChatMessage = Field(..., description="Message to add to session")
    update_context: Optional[Dict[str, Any]] = Field(
        None, description="Context updates"
    )


class SessionSearchRequest(BaseModel):
    """Request model for searching sessions"""

    user_id: Optional[str] = Field(None, description="Filter by user ID")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_after: Optional[datetime] = Field(
        None, description="Filter by creation date"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter by creation date"
    )
    limit: int = Field(default=20, description="Maximum results to return")
    offset: int = Field(default=0, description="Offset for pagination")
