from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from app.schemas.chat import VoteRequest, VoteResponse


class VoteService:
    """Service focused solely on vote/feedback operations"""

    def __init__(self):
        self.vote_storage: List[Dict[str, Any]] = []

    async def process_vote(self, request: VoteRequest) -> VoteResponse:
        """Process a vote/feedback request with enhanced validation"""
        logger.info(f"Processing vote: upvote={request.upvote}, count={request.count}")

        # Validate vote consistency
        self._validate_vote(request)

        # Store the vote
        vote_record = self._create_vote_record(request)
        self.vote_storage.append(vote_record)

        # Determine vote type and return response
        is_upvote = self._determine_vote_type(request)

        return VoteResponse(
            status="success",
            message="Vote recorded successfully",
            upvote=is_upvote,
            count=request.count,
        )

    async def get_vote_statistics(self) -> Dict[str, Any]:
        """Get voting statistics"""
        total_votes = len(self.vote_storage)
        upvotes = sum(1 for vote in self.vote_storage if vote.get("upvote", False))
        downvotes = total_votes - upvotes

        return {
            "total_votes": total_votes,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "upvote_percentage": (
                (upvotes / total_votes * 100) if total_votes > 0 else 0
            ),
        }

    async def get_recent_votes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent votes"""
        return sorted(
            self.vote_storage, key=lambda x: x.get("timestamp", ""), reverse=True
        )[:limit]

    def _validate_vote(self, request: VoteRequest) -> None:
        """Validate vote request consistency"""
        if request.downvote is not None and request.upvote == request.downvote:
            raise ValueError("Vote cannot be both upvote and downvote")

    def _create_vote_record(self, request: VoteRequest) -> Dict[str, Any]:
        """Create a vote record from the request"""
        return {
            "user_query": request.user_query,
            "chatbot_response": request.chatbot_response,
            "upvote": request.upvote,
            "downvote": request.downvote,
            "count": request.count,
            "reason_multiple_choice": request.reason_multiple_choice,
            "additional_comments": request.additional_comments,
            "date": request.date,
            "time": request.time,
            "email_address": request.email_address,
            "timestamp": datetime.now().isoformat(),
        }

    def _determine_vote_type(self, request: VoteRequest) -> bool:
        """Determine if this is primarily an upvote or downvote"""
        return request.upvote if request.downvote is None else not request.downvote


# Create singleton instance
vote_service = VoteService()
