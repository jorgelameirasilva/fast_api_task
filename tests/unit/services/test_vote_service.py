import pytest
from datetime import datetime

from app.services.vote_service import VoteService
from app.schemas.chat import VoteRequest, VoteResponse


class TestVoteService:
    """Unit tests for VoteService"""

    @pytest.mark.asyncio
    async def test_process_vote_upvote_success(self, sample_vote_request):
        """Test successful upvote processing"""
        # Arrange
        vote_service = VoteService()

        # Act
        response = await vote_service.process_vote(sample_vote_request)

        # Assert
        assert isinstance(response, VoteResponse)
        assert response.status == "success"
        assert response.message == "Vote recorded successfully"
        assert response.upvote is True
        assert response.count == 1
        assert len(vote_service.vote_storage) == 1

    @pytest.mark.asyncio
    async def test_process_vote_downvote(self, vote_service):
        """Test downvote processing"""
        # Arrange
        request = VoteRequest(
            user_query="Test query",
            chatbot_response="Test response",
            upvote=False,
            count=1,
        )

        # Act
        response = await vote_service.process_vote(request)

        # Assert
        assert response.upvote is False
        assert response.status == "success"

    @pytest.mark.asyncio
    async def test_process_vote_with_downvote_field(self, vote_service):
        """Test vote processing with explicit downvote field"""
        # Arrange
        request = VoteRequest(
            user_query="Test query",
            chatbot_response="Test response",
            upvote=False,
            downvote=True,
            count=1,
        )

        # Act
        response = await vote_service.process_vote(request)

        # Assert
        assert response.upvote is False  # downvote takes priority

    @pytest.mark.asyncio
    async def test_process_vote_conflicting_votes(self, vote_service):
        """Test vote processing with conflicting upvote/downvote"""
        # Arrange
        request = VoteRequest(
            user_query="Test query",
            chatbot_response="Test response",
            upvote=True,
            downvote=True,  # Conflicting votes
            count=1,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Vote cannot be both upvote and downvote"):
            await vote_service.process_vote(request)

    @pytest.mark.asyncio
    async def test_process_vote_with_additional_fields(self, vote_service):
        """Test vote processing with all optional fields"""
        # Arrange
        request = VoteRequest(
            user_query="Complex query",
            chatbot_response="Detailed response",
            upvote=True,
            count=5,
            reason_multiple_choice="very_helpful",
            additional_comments="Excellent response with great detail!",
            date="2024-01-15",
            time="14:30:00",
            email_address="user@example.com",
        )

        # Act
        response = await vote_service.process_vote(request)

        # Assert
        assert response.status == "success"
        assert response.count == 5

        # Check stored vote record
        vote_record = vote_service.vote_storage[0]
        assert vote_record["reason_multiple_choice"] == "very_helpful"
        assert (
            vote_record["additional_comments"]
            == "Excellent response with great detail!"
        )
        assert vote_record["email_address"] == "user@example.com"
        assert "timestamp" in vote_record

    @pytest.mark.asyncio
    async def test_get_vote_statistics_empty(self, vote_service):
        """Test getting vote statistics with no votes"""
        # Act
        stats = await vote_service.get_vote_statistics()

        # Assert
        assert stats["total_votes"] == 0
        assert stats["upvotes"] == 0
        assert stats["downvotes"] == 0
        assert stats["upvote_percentage"] == 0

    @pytest.mark.asyncio
    async def test_get_vote_statistics_with_votes(self, vote_service):
        """Test getting vote statistics with mixed votes"""
        # Arrange - Add some votes
        upvote_request = VoteRequest(
            user_query="Query 1", chatbot_response="Response 1", upvote=True, count=1
        )
        downvote_request = VoteRequest(
            user_query="Query 2", chatbot_response="Response 2", upvote=False, count=1
        )

        await vote_service.process_vote(upvote_request)
        await vote_service.process_vote(upvote_request)  # Another upvote
        await vote_service.process_vote(downvote_request)

        # Act
        stats = await vote_service.get_vote_statistics()

        # Assert
        assert stats["total_votes"] == 3
        assert stats["upvotes"] == 2
        assert stats["downvotes"] == 1
        assert stats["upvote_percentage"] == 66.66666666666666

    @pytest.mark.asyncio
    async def test_get_recent_votes_empty(self, vote_service):
        """Test getting recent votes with no votes"""
        # Act
        recent_votes = await vote_service.get_recent_votes()

        # Assert
        assert recent_votes == []

    @pytest.mark.asyncio
    async def test_get_recent_votes_with_limit(self, vote_service):
        """Test getting recent votes with limit"""
        # Arrange - Add multiple votes
        for i in range(15):
            request = VoteRequest(
                user_query=f"Query {i}",
                chatbot_response=f"Response {i}",
                upvote=True,
                count=1,
            )
            await vote_service.process_vote(request)

        # Act
        recent_votes = await vote_service.get_recent_votes(limit=5)

        # Assert
        assert len(recent_votes) == 5
        # Should be in reverse chronological order (most recent first)
        assert recent_votes[0]["user_query"] == "Query 14"
        assert recent_votes[4]["user_query"] == "Query 10"

    @pytest.mark.asyncio
    async def test_validate_vote_valid(self, vote_service):
        """Test vote validation with valid votes"""
        # Arrange
        valid_requests = [
            VoteRequest(user_query="Q", chatbot_response="R", upvote=True, count=1),
            VoteRequest(user_query="Q", chatbot_response="R", upvote=False, count=1),
            VoteRequest(
                user_query="Q",
                chatbot_response="R",
                upvote=True,
                downvote=False,
                count=1,
            ),
            VoteRequest(
                user_query="Q",
                chatbot_response="R",
                upvote=False,
                downvote=True,
                count=1,
            ),
        ]

        # Act & Assert - Should not raise any exceptions
        for request in valid_requests:
            vote_service._validate_vote(request)

    @pytest.mark.asyncio
    async def test_validate_vote_invalid(self, vote_service):
        """Test vote validation with invalid votes"""
        # Arrange
        invalid_request = VoteRequest(
            user_query="Q", chatbot_response="R", upvote=True, downvote=True, count=1
        )

        # Act & Assert
        with pytest.raises(ValueError):
            vote_service._validate_vote(invalid_request)

    @pytest.mark.asyncio
    async def test_create_vote_record(self, vote_service, sample_vote_request):
        """Test creating vote record from request"""
        # Act
        vote_record = vote_service._create_vote_record(sample_vote_request)

        # Assert
        assert vote_record["user_query"] == sample_vote_request.user_query
        assert vote_record["chatbot_response"] == sample_vote_request.chatbot_response
        assert vote_record["upvote"] == sample_vote_request.upvote
        assert vote_record["count"] == sample_vote_request.count
        assert (
            vote_record["reason_multiple_choice"]
            == sample_vote_request.reason_multiple_choice
        )
        assert (
            vote_record["additional_comments"]
            == sample_vote_request.additional_comments
        )
        assert "timestamp" in vote_record

    @pytest.mark.asyncio
    async def test_determine_vote_type_upvote(self, vote_service):
        """Test determining vote type for upvote"""
        # Arrange
        request = VoteRequest(
            user_query="Q", chatbot_response="R", upvote=True, count=1
        )

        # Act
        is_upvote = vote_service._determine_vote_type(request)

        # Assert
        assert is_upvote is True

    @pytest.mark.asyncio
    async def test_determine_vote_type_downvote(self, vote_service):
        """Test determining vote type for downvote"""
        # Arrange
        request = VoteRequest(
            user_query="Q", chatbot_response="R", upvote=False, count=1
        )

        # Act
        is_upvote = vote_service._determine_vote_type(request)

        # Assert
        assert is_upvote is False

    @pytest.mark.asyncio
    async def test_determine_vote_type_with_downvote_field(self, vote_service):
        """Test determining vote type with explicit downvote field"""
        # Arrange
        request = VoteRequest(
            user_query="Q", chatbot_response="R", upvote=False, downvote=True, count=1
        )

        # Act
        is_upvote = vote_service._determine_vote_type(request)

        # Assert
        assert is_upvote is False

    @pytest.mark.asyncio
    async def test_vote_storage_accumulation(self, vote_service):
        """Test that votes accumulate in storage"""
        # Arrange
        requests = [
            VoteRequest(user_query="Q1", chatbot_response="R1", upvote=True, count=1),
            VoteRequest(user_query="Q2", chatbot_response="R2", upvote=False, count=1),
            VoteRequest(user_query="Q3", chatbot_response="R3", upvote=True, count=1),
        ]

        # Act
        for request in requests:
            await vote_service.process_vote(request)

        # Assert
        assert len(vote_service.vote_storage) == 3
        assert vote_service.vote_storage[0]["user_query"] == "Q1"
        assert vote_service.vote_storage[1]["user_query"] == "Q2"
        assert vote_service.vote_storage[2]["user_query"] == "Q3"

    @pytest.mark.asyncio
    async def test_vote_timestamp_format(self, vote_service, sample_vote_request):
        """Test that vote timestamps are in ISO format"""
        # Act
        await vote_service.process_vote(sample_vote_request)

        # Assert
        vote_record = vote_service.vote_storage[0]
        timestamp_str = vote_record["timestamp"]

        # Should be able to parse as ISO format
        parsed_timestamp = datetime.fromisoformat(timestamp_str)
        assert isinstance(parsed_timestamp, datetime)
