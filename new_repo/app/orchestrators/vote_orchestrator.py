"""
Vote Orchestrator - Handles vote operations following SOLID principles
"""

import logging
from typing import Any

from app.models.document import MessageDocument, MessageVoteRequest
from app.services.cosmos_service import create_cosmos_service

logger = logging.getLogger(__name__)


class VoteOrchestrator:
    """Orchestrates vote operations"""

    def __init__(self):
        self.cosmos_service = create_cosmos_service()

    async def process_vote(
        self, request: MessageVoteRequest, current_user: dict[str, Any]
    ) -> MessageDocument:
        """Process a vote on a message"""
        try:
            user_id = current_user.get("oid", "default_user")
            logger.info(
                f"Processing vote for message {request.message_id} by user {user_id}"
            )

            # Use cosmos service to process the vote
            updated_message = await self.cosmos_service.vote_message(request, user_id)

            if not updated_message:
                raise ValueError(f"Failed to vote on message {request.message_id}")

            return updated_message

        except Exception as e:
            logger.error(f"Error processing vote: {str(e)}")
            raise

    async def remove_vote(
        self, message_id: str, current_user: dict[str, Any]
    ) -> MessageDocument:
        """Remove a vote from a message"""
        try:
            user_id = current_user.get("oid", "default_user")
            logger.info(f"Removing vote for message {message_id} by user {user_id}")

            # Create remove vote request
            remove_request = MessageVoteRequest(
                message_id=message_id, upvote=0, downvote=0, feedback=None
            )

            updated_message = await self.cosmos_service.vote_message(
                remove_request, user_id
            )

            if not updated_message:
                raise ValueError(f"Failed to remove vote from message {message_id}")

            return updated_message

        except Exception as e:
            logger.error(f"Error removing vote: {str(e)}")
            raise

    async def get_message_with_vote(
        self, message_id: str, current_user: dict[str, Any]
    ) -> MessageDocument:
        """Get a message with its vote information"""
        try:
            user_id = current_user.get("oid", "default_user")
            logger.info(f"Getting message {message_id} for user {user_id}")

            message = await self.cosmos_service.get_message(message_id, user_id)

            if not message:
                raise ValueError(f"Message {message_id} not found for user {user_id}")

            return message

        except Exception as e:
            logger.error(f"Error getting message: {str(e)}")
            raise


# Global instance
vote_orchestrator = VoteOrchestrator()
