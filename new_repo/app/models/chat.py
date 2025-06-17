"""Pydantic models for chat API"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Individual chat message"""

    role: str = Field(
        ..., description="Role of the message sender (user/assistant/system)"
    )
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Chat request model"""

    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    session_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Session state"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")


class ChatContext(BaseModel):
    """Chat context with overrides"""

    overrides: Optional[Dict[str, Any]] = Field(
        None, description="Chat context with overrides"
    )
    session_state: Optional[str] = Field(None, description="Session state")


class ChatDelta(BaseModel):
    """Schema for chat response delta"""

    role: Optional[str] = Field(None, description="Role of the message")
    content: Optional[str] = Field(None, description="Content delta")


class ChatContentData(BaseModel):
    """Schema for chat content data"""

    data_points: Optional[List[str]] = Field(
        None, description="Data points from retrieval"
    )
    thoughts: Optional[str] = Field(None, description="Assistant thoughts")


class ChatChoice(BaseModel):
    """Schema for chat response choice"""

    delta: Optional[ChatDelta] = Field(
        None, description="Delta for streaming responses"
    )
    message: Optional[ChatMessage] = Field(
        None, description="Complete message for non-streaming"
    )
    content: Optional[ChatContentData] = Field(
        None, description="Structured content data"
    )
    function_call: Optional[Dict[str, Any]] = Field(
        None, description="Function call information"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="Tool calls information"
    )
    finish_reason: Optional[str] = Field(None, description="Reason for completion")


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    choices: List[ChatChoice] = Field(..., description="List of response choices")
    session_state: Optional[str] = Field(None, description="Updated session state")
    context: Optional[ChatContext] = Field(None, description="Updated chat context")


class StreamingChatResponse(BaseModel):
    """Streaming chat response chunk"""

    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    created: Optional[int] = Field(default=None, description="Creation timestamp")
    id: Optional[str] = Field(default=None, description="Response ID")
    model: Optional[str] = Field(default=None, description="Model used")
    object: Optional[str] = Field(default=None, description="Object type")
