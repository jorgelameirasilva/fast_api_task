from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Schema for a single chat message"""

    role: str = Field(
        ..., description="Role of the message sender (user, assistant, system)"
    )
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[datetime] = Field(None, description="Timestamp of the message")


class ChatRequest(BaseModel):
    """Schema for chat requests"""

    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context for the chat"
    )
    session_state: Optional[str] = Field(None, description="Session state identifier")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    message: ChatMessage = Field(..., description="The response message")
    session_state: Optional[str] = Field(None, description="Updated session state")
    context: Optional[Dict[str, Any]] = Field(None, description="Updated context")


class AskRequest(BaseModel):
    """Schema for ask requests"""

    user_query: str = Field(..., min_length=1, description="The user's query")
    user_query_vector: Optional[List[float]] = Field(
        None, description="Vector representation of the query"
    )
    chatbot_response: Optional[str] = Field(
        None, description="Previous chatbot response for context"
    )
    count: Optional[int] = Field(0, description="Request count")
    upvote: Optional[bool] = Field(
        None, description="Whether this is an upvote request"
    )


class AskResponse(BaseModel):
    """Schema for ask responses"""

    user_query: str = Field(..., description="The original user query")
    chatbot_response: str = Field(..., description="The chatbot's response")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Response context"
    )
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source documents"
    )
    count: int = Field(0, description="Response count")


class VoteRequest(BaseModel):
    """Schema for vote/feedback requests"""

    user_query: str = Field(..., description="The original user query")
    chatbot_response: str = Field(
        ..., description="The chatbot response being voted on"
    )
    count: int = Field(..., description="Vote count")
    upvote: bool = Field(
        ..., description="Whether this is an upvote (True) or downvote (False)"
    )


class VoteResponse(BaseModel):
    """Schema for vote responses"""

    status: str = Field(..., description="Status of the vote operation")
    message: str = Field(..., description="Response message")
    upvote: bool = Field(..., description="The vote type recorded")
    count: int = Field(..., description="Updated count")


class AuthSetupResponse(BaseModel):
    """Schema for authentication setup response"""

    auth_enabled: bool = Field(..., description="Whether authentication is enabled")
    auth_type: Optional[str] = Field(None, description="Type of authentication")
    login_url: Optional[str] = Field(None, description="Login URL if applicable")
    logout_url: Optional[str] = Field(None, description="Logout URL if applicable")
