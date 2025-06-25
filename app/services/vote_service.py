"""Vote service for handling voting business logic"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VoteService:
    """Service for handling vote operations"""

    def __init__(self):
        # In-memory storage for demo purposes
        self.votes: dict[str, dict[str, Any]] = {}

    async def process_vote(self, vote_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process a vote request

        Args:
            vote_data: Dictionary containing vote information

        Returns:
            Dictionary with processing result
        """
        try:
            # Generate a simple vote ID
            vote_id = f"vote_{len(self.votes) + 1}"

            # Store the vote
            self.votes[vote_id] = {
                "id": vote_id,
                "user_query": vote_data.get("user_query"),
                "chatbot_response": vote_data.get("chatbot_response"),
                "upvote": vote_data.get("upvote", 0),
                "downvote": vote_data.get("downvote", 0),
                "count": vote_data.get("count", 0),
                "reason_multiple_choice": vote_data.get("reason_multiple_choice"),
                "additional_comments": vote_data.get("additional_comments"),
                "processed": True,
            }

            logger.info(f"Processed vote {vote_id}")

            return {
                "vote_id": vote_id,
                "status": "success",
                "message": "Vote processed successfully",
            }

        except Exception as e:
            logger.error(f"Error processing vote: {str(e)}")
            return {"status": "error", "message": f"Failed to process vote: {str(e)}"}

    async def get_vote_stats(self) -> dict[str, Any]:
        """Get voting statistics"""
        try:
            total_votes = len(self.votes)
            upvotes = sum(
                1 for vote in self.votes.values() if vote.get("upvote", 0) > 0
            )
            downvotes = sum(
                1 for vote in self.votes.values() if vote.get("downvote", 0) > 0
            )

            return {
                "total_votes": total_votes,
                "upvotes": upvotes,
                "downvotes": downvotes,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error getting vote stats: {str(e)}")
            return {"status": "error", "message": f"Failed to get vote stats: {str(e)}"}


# Global instance
vote_service = VoteService()
