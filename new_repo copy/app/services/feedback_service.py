"""
Feedback Service - Handles feedback business logic following SOLID principles
Single Responsibility: Manage feedback storage and processing
"""

import uuid
from datetime import datetime
from loguru import logger

from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackEntity
from app.core.setup import get_table_service_client


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

            # Try to use table storage
            table_service_client = get_table_service_client()
            if table_service_client:
                # Get the feedback table client
                table_client = table_service_client.get_table_client("feedback")

                # Convert entity to dict format expected by Azure Storage
                entity_dict = {
                    "PartitionKey": entity.partition_key,
                    "RowKey": entity.row_key,
                    "Comment": entity.comment,
                    "Feedback": entity.feedback,
                    "SubmittedAt": entity.submitted_at.isoformat(),
                }

                # Add optional name if provided
                if entity.name:
                    entity_dict["Name"] = entity.name

                # Store the entity
                await table_client.create_entity(entity=entity_dict)
                logger.info(f"Feedback entity stored in table storage: {entity_dict}")
            else:
                # Fallback to logging only
                logger.info(
                    f"No table client available - logging feedback entity: {entity.model_dump()}"
                )

            return FeedbackResponse(
                message="Entity stored",
                row_key=row_key,
            )

        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            raise


# Create service instance
feedback_service = FeedbackService()
