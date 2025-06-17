"""Pydantic models for chat API"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Schema for a single chat message"""

    role: str = Field(
        ..., description="Role of the message sender (user, assistant, system)"
    )
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[datetime] = Field(None, description="Timestamp of the message")


class Overrides(BaseModel):
    """Schema for context overrides"""

    selected_category: Optional[str] = Field(
        None, description="Selected category for filtering"
    )
    top: Optional[int] = Field(3, description="Number of top results to retrieve")
    retrieval_mode: Optional[str] = Field(
        "hybrid", description="Retrieval mode (hybrid, vector, etc.)"
    )
    semantic_ranker: Optional[bool] = Field(
        True, description="Whether to use semantic ranker"
    )
    semantic_captions: Optional[bool] = Field(
        False, description="Whether to use semantic captions"
    )
    suggest_followup_questions: Optional[bool] = Field(
        True, description="Whether to suggest followup questions"
    )
    use_oid_security_filter: Optional[bool] = Field(
        False, description="Whether to use OID security filter"
    )
    use_groups_security_filter: Optional[bool] = Field(
        False, description="Whether to use groups security filter"
    )


class ChatContext(BaseModel):
    """Schema for chat context"""

    overrides: Optional[Overrides] = Field(
        None, description="Override settings for the chat"
    )


class ChatRequest(BaseModel):
    """Schema for chat requests"""

    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    context: Optional[ChatContext] = Field(
        None, description="Chat context with overrides"
    )
    session_state: Optional[str] = Field(None, description="Session state identifier")


class ChatDelta(BaseModel):
    """Schema for chat response delta"""

    role: Optional[str] = Field(None, description="Role of the message sender")
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
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls")
    finish_reason: Optional[str] = Field(None, description="Reason for finishing")


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    choices: List[ChatChoice] = Field(..., description="List of response choices")
    session_state: Optional[str] = Field(None, description="Updated session state")
    context: Optional[ChatContext] = Field(None, description="Updated context")
