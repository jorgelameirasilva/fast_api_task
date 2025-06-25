"""Pydantic models for chat API"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Chat message model"""

    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime | None = Field(
        default=None, description="Timestamp of the message"
    )


class ChatDelta(BaseModel):
    """Chat delta for streaming responses"""

    role: str | None = Field(default=None, description="Role of the message sender")
    content: str | None = Field(default=None, description="Content delta")


class ChatContentData(BaseModel):
    """Additional content data for chat responses"""

    data_points: list[str] = Field(default_factory=list, description="Data points used")
    thoughts: str = Field(default="", description="Reasoning thoughts")


class ChatChoice(BaseModel):
    """Chat choice model"""

    message: ChatMessage | None = Field(default=None, description="Complete message")
    delta: ChatDelta | None = Field(default=None, description="Delta for streaming")
    content: ChatContentData | None = Field(
        default=None, description="Additional content data"
    )
    finish_reason: str | None = Field(default=None, description="Reason for finishing")


class Overrides(BaseModel):
    """Override settings for chat requests"""

    selected_category: str | None = Field(default=None, description="Selected category")
    top: int = Field(default=3, description="Number of top results")
    retrieval_mode: str | None = Field(default=None, description="Retrieval mode")
    semantic_ranker: bool = Field(default=True, description="Use semantic ranker")
    semantic_captions: bool = Field(default=False, description="Use semantic captions")
    suggest_followup_questions: bool = Field(
        default=False, description="Suggest followup questions"
    )
    use_oid_security_filter: bool = Field(
        default=False, description="Use OID security filter"
    )
    use_groups_security_filter: bool = Field(
        default=False, description="Use groups security filter"
    )


class ChatContext(BaseModel):
    """Chat context model"""

    overrides: Overrides | None = Field(default=None, description="Override settings")


class ChatRequest(BaseModel):
    """Chat request model"""

    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    stream: bool = Field(default=False, description="Whether to stream the response")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    session_state: str | None = Field(
        default=None, description="Session state identifier"
    )

    @field_validator("messages")
    @classmethod
    def validate_messages_not_empty(cls, v):
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v


class ChatResponse(BaseModel):
    """Chat response model"""

    choices: list[ChatChoice] = Field(..., description="List of response choices")
    session_state: str | None = Field(
        default=None, description="Session state identifier"
    )
    context: ChatContext | None = Field(default=None, description="Response context")
