"""
Feedback Orchestrator - Orchestrates feedback requests following SOLID principles
Single Responsibility: Coordinates between services and handles response formatting
"""

import logging
from typing import Any

from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import feedback_service

logger = logging.getLogger(__name__)


class FeedbackOrchestrator:
    """
    Orchestrates feedback requests following SOLID principles
    Single Responsibility: Coordinate feedback processing and response formatting
    """

    def __init__(self):
        pass

    async def submit_feedback(
        self, request: FeedbackRequest, current_user: dict[str, Any]
    ) -> FeedbackResponse:
        """
        Process feedback submission - orchestrates the flow
        """
        try:
            user_id = current_user.get("oid", "anonymous")
            logger.info(f"Feedback submission from user: {user_id}")

            # Process feedback through service
            result = await feedback_service.submit_feedback(request, user_id)

            return result

        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            raise


# Global instance
feedback_orchestrator = FeedbackOrchestrator()
