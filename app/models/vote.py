"""Pydantic models for vote API"""

from pydantic import BaseModel, Field, field_validator, model_validator


class VoteRequest(BaseModel):
    """Vote request model"""

    user_query: str | dict = Field(..., description="User query text")
    chatbot_response: str | dict = Field(..., description="Chatbot response text")
    upvote: int = Field(..., description="Upvote value (0 or 1)")
    downvote: int = Field(..., description="Downvote value (0 or 1)")
    count: int = Field(..., description="Count value (1 or -1)")
    reason_multiple_choice: str | dict | None = Field(
        default=None, description="Reason for downvote"
    )
    additional_comments: str | dict | None = Field(
        default=None, description="Additional comments"
    )

    # Allow extra fields for compatibility
    class Config:
        extra = "allow"

    @field_validator("upvote")
    @classmethod
    def validate_upvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(
                f"Upvote must be either 1 or 0 (<<class 'int'>), but got {v} ({type(v)})"
            )
        return v

    @field_validator("downvote")
    @classmethod
    def validate_downvote(cls, v):
        if v not in [0, 1]:
            raise ValueError(
                f"Downvote must be either 1 or 0 (<<class 'int'>), but got {v} ({type(v)})"
            )
        return v

    @field_validator("count")
    @classmethod
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

    @field_validator("user_query")
    @classmethod
    def validate_user_query(cls, v):
        if not isinstance(v, str) and v != {}:
            raise ValueError(
                f"If user_query provided, it expects a string, but got {type(v)}"
            )
        if isinstance(v, str) and (v == "" or v is None):
            raise ValueError("user_query cannot be empty")
        return v

    @field_validator("chatbot_response")
    @classmethod
    def validate_chatbot_response(cls, v):
        if not isinstance(v, str) and v != {}:
            raise ValueError(
                f"If chatbot_response, it expects a string, but got {type(v)}"
            )
        return v

    @field_validator("reason_multiple_choice")
    @classmethod
    def validate_reason_multiple_choice(cls, v):
        if v is not None and not isinstance(v, str) and v != {}:
            raise ValueError(
                f"reason_multiple_choice must be a string, but got {type(v)}"
            )
        return v

    @field_validator("additional_comments")
    @classmethod
    def validate_additional_comments(cls, v):
        if v is not None and not isinstance(v, str) and v != {}:
            raise ValueError(f"additional_comments must be a string, but got {type(v)}")
        return v


class VoteResponse(BaseModel):
    """Vote response model"""

    user_query: str | dict = Field(..., description="User query")
    chatbot_response: str | dict = Field(..., description="Chatbot response")
    upvote: int = Field(..., description="Upvote value")
    downvote: int = Field(..., description="Downvote value")
    count: int = Field(..., description="Count value")
