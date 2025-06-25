"""
Vote Orchestrator

Orchestrates the complete vote workflow following SOLID principles.
Coordinates vote processing, logging, and response formatting.
"""

import logging
from typing import Any

from app.models.vote import VoteRequest, VoteResponse
from app.services.vote_service import VoteService

logger = logging.getLogger(__name__)


class VoteOrchestrator:
    """
    Orchestrates the complete vote workflow.

    Responsibilities:
    - Coordinate vote processing services
    - Handle vote workflow logic
    - Manage vote response formatting
    - Provide clean interface for vote operations
    """

    def __init__(self, vote_service: VoteService):
        """
        Initialize orchestrator with required services.

        Args:
            vote_service: Service for vote processing
        """
        self.vote_service = vote_service
        self.logger = logging.getLogger(__name__)

    async def process_vote_request(
        self, request: VoteRequest, auth_claims: dict[str, Any]
    ) -> VoteResponse:
        """
        Process a complete vote request workflow.

        Args:
            request: The vote request data
            auth_claims: Authentication claims from JWT

        Returns:
            VoteResponse: Processed vote response

        Raises:
            Exception: If vote processing fails
        """
        try:
            self.logger.info(
                "Processing vote request",
                extra={
                    "user_id": auth_claims.get("oid", "unknown"),
                    "vote_type": "upvote" if request.upvote else "downvote",
                },
            )

            # Convert request to dict for the service
            vote_data = {
                "user_query": request.user_query,
                "chatbot_response": request.chatbot_response,
                "upvote": request.upvote,
                "downvote": request.downvote,
                "count": request.count,
                "reason_multiple_choice": request.reason_multiple_choice,
                "additional_comments": request.additional_comments,
            }

            # Process the vote using the vote service
            service_response = await self.vote_service.process_vote(vote_data)

            # Convert service response back to VoteResponse model
            response = VoteResponse(
                user_query=request.user_query,
                message=request.chatbot_response,
                upvote=request.upvote,
                downvote=request.downvote,
                count=request.count,
            )

            self.logger.info(
                "Vote processed successfully",
                extra={
                    "user_id": auth_claims.get("oid", "unknown"),
                    "vote_type": "upvote" if request.upvote else "downvote",
                    "vote_id": service_response.get("vote_id"),
                },
            )

            return response

        except Exception as e:
            self.logger.error(
                "Vote processing failed",
                extra={"user_id": auth_claims.get("oid", "unknown"), "error": str(e)},
            )
            raise
