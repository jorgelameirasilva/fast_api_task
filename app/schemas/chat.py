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

    user_query: str = Field(..., min_length=1, description="The original user query")
    chatbot_response: str = Field(
        ..., min_length=1, description="The chatbot response being voted on"
    )
    count: int = Field(..., ge=0, description="Vote count (must be non-negative)")
    upvote: bool = Field(
        ..., description="Whether this is an upvote (True) or downvote (False)"
    )

    # Additional optional fields for enhanced feedback
    downvote: Optional[bool] = Field(None, description="Explicit downvote flag")
    reason_multiple_choice: Optional[str] = Field(
        None, description="Predefined reason for the vote"
    )
    additional_comments: Optional[str] = Field(
        None, description="Additional user comments"
    )
    date: Optional[str] = Field(None, description="Date of the vote")
    time: Optional[str] = Field(None, description="Time of the vote")
    email_address: Optional[str] = Field(None, description="User's email address")


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
