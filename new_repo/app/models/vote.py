"""Pydantic models for vote API"""

from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator, model_validator


class VoteRequest(BaseModel):
    """Vote request model"""

    user_query: Union[str, Dict] = Field(..., description="User query text")
    chatbot_response: Union[str, Dict] = Field(..., description="Chatbot response text")
    upvote: int = Field(..., description="Upvote value (0 or 1)")
    downvote: int = Field(..., description="Downvote value (0 or 1)")
    count: int = Field(..., description="Count value (1 or -1)")
    reason_multiple_choice: Optional[Union[str, Dict]] = Field(
        default=None, description="Reason for downvote"
    )
    additional_comments: Optional[Union[str, Dict]] = Field(
        default=None, description="Additional comments"
    )

    # Allow extra fields for compatibility
    class Config:
        extra = "allow"

    @validator("upvote")
    def validate_upvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(
                f"Upvote must be either 1 or 0 (<<class 'int'>), but got {v} ({type(v)})"
            )
        return v

    @validator("downvote")
    def validate_downvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(
                f"Downvote must be either 1 or 0 (<<class 'int'>), but got {v} ({type(v)})"
            )
        return v

    @validator("count")
    def validate_count(cls, v):
        if v not in [-1, 1]:
            raise ValueError(f"Count must be either 1 or -1, but got {v}.")
        return v

    @model_validator(mode="after")
    def validate_vote_combination(self):
        upvote = self.upvote
        downvote = self.downvote

        if upvote == 1 and downvote == 1:
            raise ValueError("Both upvote and downvote were recorded simultaneously.")
        elif upvote == 0 and downvote == 0:
            raise ValueError("Neither an upvote nor a downvote were recorded.")
        return self

    @validator("user_query")
    def validate_user_query(cls, v):
        if not isinstance(v, str) and v != {}:
            raise ValueError(
                f"If user_query provided, it expects a string, but got {type(v)}"
            )
        if isinstance(v, str) and (v == "" or v is None):
            raise ValueError("user_query cannot be empty")
        return v

    @validator("chatbot_response")
    def validate_chatbot_response(cls, v):
        if not isinstance(v, str) and v != {}:
            raise ValueError(
                f"If chatbot_response, it expects a string, but got {type(v)}"
            )
        return v

    @validator("reason_multiple_choice")
    def validate_reason_multiple_choice(cls, v):
        if v is not None and not isinstance(v, str) and v != {}:
            raise ValueError(
                f"reason_multiple_choice must be a string, but got {type(v)}"
            )
        return v

    @validator("additional_comments")
    def validate_additional_comments(cls, v):
        if v is not None and not isinstance(v, str) and v != {}:
            raise ValueError(f"additional_comments must be a string, but got {type(v)}")
        return v


class VoteResponse(BaseModel):
    """Vote response model"""

    user_query: Union[str, Dict] = Field(..., description="User query")
    message: Union[str, Dict] = Field(
        ..., description="Chatbot response (renamed from chatbot_response)"
    )
    upvote: int = Field(..., description="Upvote value")
    downvote: int = Field(..., description="Downvote value")
    count: int = Field(..., description="Count value")
