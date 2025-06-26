"""
Vote Orchestrator - Simple orchestration matching original app.py
"""

import logging
from typing import Any

from app.models.vote import VoteRequest, VoteResponse
from app.services.vote_service import VoteService

logger = logging.getLogger(__name__)


class VoteOrchestrator:
    """Simple vote orchestrator - just calls service and returns result"""

    def __init__(self, vote_service: VoteService):
        self.vote_service = vote_service

    async def process_vote_request(
        self, request: VoteRequest, auth_claims: dict[str, Any]
    ) -> VoteResponse:
        """
        Process vote request - simple pass-through to service

        Args:
            request: The vote request data
            auth_claims: Authentication claims from JWT

        Returns:
            VoteResponse: The vote response from service
        """
        try:
            logger.info("Vote request received")

            # Process the vote using the service - pass request directly
            response = await self.vote_service.process_vote(request)

            logger.info("Vote processed successfully")
            return response

        except Exception as e:
            logger.error(f"Vote processing failed: {str(e)}")
            raise
