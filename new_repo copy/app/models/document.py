"""Simple message document schema for database storage"""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class MessageContent(BaseModel):
    """Message content with role and text"""

    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message text content")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ["user", "assistant"]:
            raise ValueError("Role must be either 'user' or 'assistant'")
        return v


class MessageDocument(BaseModel):
    """
    Simple message document model for database storage
    Each document represents a single message with all associated metadata
    """

    id: str = Field(..., description="Message UUID (MongoDB document ID)")
    session_id: str = Field(..., description="Session UUID grouping messages")
    user_id: str = Field(..., description="User identifier for security")
    title: Optional[str] = Field(
        default=None,
        description="Session title (auto-generated from first user message)",
    )
    message: MessageContent = Field(..., description="Message content with role")
    knowledge_base: Optional[str] = Field(
        default=None, description="Knowledge base used"
    )
    upvote: int = Field(default=0, description="Upvote value (0 or 1)")
    downvote: int = Field(default=0, description="Downvote value (0 or 1)")
    feedback: Optional[str] = Field(default=None, description="Optional vote feedback")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Message creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )
    voted_at: Optional[datetime] = Field(default=None, description="Vote timestamp")
    is_active: bool = Field(default=True, description="Whether message is active")

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v):
        if isinstance(v, MessageContent):
            return v
        elif isinstance(v, dict):
            return MessageContent(**v)
        # Let pydantic handle other types
        return v

    @field_validator("upvote")
    @classmethod
    def validate_upvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(f"Upvote must be either 1 or 0, but got {v}")
        return v

    @field_validator("downvote")
    @classmethod
    def validate_downvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(f"Downvote must be either 1 or 0, but got {v}")
        return v

    @model_validator(mode="after")
    def validate_vote_combination(self):
        # Allow both to be 0 (no vote yet), but not both to be 1
        if self.upvote == 1 and self.downvote == 1:
            raise ValueError("Both upvote and downvote cannot be 1 simultaneously.")
        return self


class MessageCreateRequest(BaseModel):
    """Request to create a new message"""

    session_id: Optional[str] = Field(
        default=None, description="Session ID (optional, will create if not provided)"
    )
    message: MessageContent = Field(..., description="Message content")
    knowledge_base: Optional[str] = Field(
        default=None, description="Knowledge base used"
    )


class MessageVoteRequest(BaseModel):
    """Request to vote on a message"""

    message_id: str = Field(..., description="Message ID to vote on")
    upvote: int = Field(..., description="Upvote value (0 or 1)")
    downvote: int = Field(..., description="Downvote value (0 or 1)")
    feedback: Optional[str] = Field(default=None, description="Optional vote feedback")

    @field_validator("upvote")
    @classmethod
    def validate_upvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(f"Upvote must be either 1 or 0, but got {v}")
        return v

    @field_validator("downvote")
    @classmethod
    def validate_downvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(f"Downvote must be either 1 or 0, but got {v}")
        return v

    @model_validator(mode="after")
    def validate_vote_combination(self):
        upvote = self.upvote
        downvote = self.downvote

        if upvote == 1 and downvote == 1:
            raise ValueError("Both upvote and downvote cannot be 1 simultaneously.")
        elif upvote == 0 and downvote == 0:
            raise ValueError("Either upvote or downvote must be 1.")
        return self


class SessionSummary(BaseModel):
    """Session summary for listing user sessions"""

    session_id: str = Field(..., description="Session UUID")
    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(default=None, description="Session title")
    message_count: int = Field(..., description="Number of messages in session")
    created_at: datetime = Field(..., description="First message timestamp")
    updated_at: datetime = Field(..., description="Last message timestamp")
    is_active: bool = Field(default=True, description="Whether session is active")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
