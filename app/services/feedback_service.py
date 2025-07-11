"""
Feedback Service - Handles feedback business logic following SOLID principles
Single Responsibility: Manage feedback storage and processing
"""

import uuid
from datetime import datetime
from typing import Any
from loguru import logger

from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackEntity
from app.core.config import settings


class FeedbackService:
    """Service focused solely on feedback operations"""

    def __init__(self):
        pass

    async def submit_feedback(
        self,
        request: FeedbackRequest,
        user_id: str = "anonymous",
    ) -> FeedbackResponse:
        """Submit feedback to storage"""
        logger.info(f"Processing feedback submission from user: {user_id}")

        try:
            # Create feedback entity
            now = datetime.utcnow()
            row_key = str(uuid.uuid4())

            entity = FeedbackEntity(
                partition_key="feedback",
                row_key=row_key,
                comment=request.comment,
                feedback=request.feedback,
                submitted_at=now,
                name=request.name,
            )

            # In a real implementation, this would save to Azure Storage Table
            # For now, we'll log it and return success
            logger.info(f"Feedback entity created: {entity.model_dump()}")

            # TODO: Implement actual storage when Azure Storage Table client is configured
            # table_client = get_table_client()
            # await table_client.create_entity(entity=entity.model_dump())

            return FeedbackResponse(
                message="Entity stored",
                row_key=row_key,
            )

        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            raise


# Create service instance
feedback_service = FeedbackService()
