"""
Data Transfer Objects (DTOs)
Defines the API request/response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class AskRequest(BaseModel):
    """Request model for ask endpoint"""

    query: str = Field(..., description="User's question", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_results: Optional[int] = Field(
        5, description="Maximum search results", ge=1, le=20
    )


class AskResponse(BaseModel):
    """Response model for ask endpoint"""

    answer: str = Field(..., description="Generated answer")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source documents"
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score", ge=0.0, le=1.0
    )
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )


class ChatMessage(BaseModel):
    """Individual chat message"""

    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    message: str = Field(..., description="User's message", min_length=1)
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID for context"
    )
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list, description="Chat history"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    response: str = Field(..., description="Assistant's response")
    conversation_id: str = Field(..., description="Conversation ID")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source documents"
    )
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Check timestamp")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Dependency status"
    )
