"""Feedback schemas for FastAPI"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """Feedback submission request"""

    feedback: str = Field(..., description="Feedback content")
    comment: str = Field(..., description="Comment content")
    name: Optional[str] = Field(None, description="Optional name of the submitter")


class FeedbackResponse(BaseModel):
    """Feedback submission response"""

    message: str = Field(..., description="Success message")
    row_key: str = Field(..., description="Generated row key for the feedback")


class FeedbackEntity(BaseModel):
    """Feedback entity for storage"""

    partition_key: str = Field(..., description="Partition key")
    row_key: str = Field(..., description="Row key")
    comment: str = Field(..., description="Comment content")
    feedback: str = Field(..., description="Feedback content")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    name: Optional[str] = Field(None, description="Optional submitter name")
