"""
Feedback API Routes - Thin HTTP layer following SOLID principles
Single Responsibility: Handle HTTP requests and delegate to business services
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends, status

from app.api.dependencies.auth import get_current_user
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.orchestrators.feedback_orchestrator import feedback_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED
)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Submit feedback endpoint
    """
    try:
        # Process feedback through orchestrator
        result = await feedback_orchestrator.submit_feedback(request, current_user)
        return result

    except Exception as error:
        logger.error(f"Feedback endpoint error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
