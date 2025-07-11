"""
Tests for feedback endpoint functionality
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


@pytest.mark.asyncio
async def test_feedback_endpoint_success(client, sample_feedback_request):
    """Test successful feedback submission"""

    # Make request to feedback endpoint
    response = await client.post("/feedback", json=sample_feedback_request)

    # Verify we get a successful response
    assert response.status_code == 201
    assert response.headers.get("content-type") == "application/json"

    # Parse the JSON response
    data = response.json()

    # Verify response structure
    assert "message" in data
    assert "row_key" in data
    assert data["message"] == "Entity stored"
    assert isinstance(data["row_key"], str)
    assert len(data["row_key"]) > 20  # UUID should be long


@pytest.mark.asyncio
async def test_feedback_endpoint_missing_required_fields(client):
    """Test feedback endpoint with missing required fields"""

    # Test missing feedback field
    incomplete_request = {
        "comment": "Test comment"
        # Missing "feedback" field
    }

    response = await client.post("/feedback", json=incomplete_request)
    assert response.status_code == 422  # Validation error

    # Test missing comment field
    incomplete_request = {
        "feedback": "Test feedback"
        # Missing "comment" field
    }

    response = await client.post("/feedback", json=incomplete_request)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_feedback_endpoint_with_optional_name(client):
    """Test feedback endpoint with optional name field"""

    request_with_name = {
        "feedback": "Great feature!",
        "comment": "Love the new interface",
        "name": "John Doe",
    }

    response = await client.post("/feedback", json=request_with_name)

    # Verify successful response
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "row_key" in data


@pytest.mark.asyncio
async def test_feedback_endpoint_empty_request(client):
    """Test feedback endpoint with empty request"""

    response = await client.post("/feedback", json={})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_feedback_endpoint_invalid_json(client):
    """Test feedback endpoint with invalid JSON"""

    response = await client.post(
        "/feedback",
        content="invalid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422  # JSON decode error


@pytest.mark.asyncio
@patch("app.services.feedback_service.feedback_service.submit_feedback")
async def test_feedback_service_error_handling(
    mock_submit, client, sample_feedback_request
):
    """Test feedback endpoint error handling when service fails"""

    # Mock service to raise an exception
    mock_submit.side_effect = Exception("Storage service unavailable")

    response = await client.post("/feedback", json=sample_feedback_request)

    # Should return 500 error
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Storage service unavailable" in data["detail"]


@pytest.mark.asyncio
async def test_feedback_entity_model():
    """Test the feedback entity model creation"""
    from app.schemas.feedback import FeedbackEntity

    now = datetime.utcnow()

    entity = FeedbackEntity(
        partition_key="feedback",
        row_key="test-key-123",
        comment="Test comment",
        feedback="Test feedback",
        submitted_at=now,
        name="Test User",
    )

    # Verify all fields are correctly set
    assert entity.partition_key == "feedback"
    assert entity.row_key == "test-key-123"
    assert entity.comment == "Test comment"
    assert entity.feedback == "Test feedback"
    assert entity.submitted_at == now
    assert entity.name == "Test User"

    # Test serialization
    entity_dict = entity.model_dump()
    assert isinstance(entity_dict, dict)
    assert entity_dict["partition_key"] == "feedback"


@pytest.mark.asyncio
async def test_feedback_request_validation():
    """Test feedback request validation"""
    from app.schemas.feedback import FeedbackRequest
    from pydantic import ValidationError

    # Test valid request
    valid_request = FeedbackRequest(
        feedback="Great app!", comment="Very helpful", name="John"
    )
    assert valid_request.feedback == "Great app!"
    assert valid_request.name == "John"

    # Test request without optional name
    request_no_name = FeedbackRequest(feedback="Good stuff", comment="Works well")
    assert request_no_name.name is None

    # Test invalid request - missing required fields
    with pytest.raises(ValidationError):
        FeedbackRequest(feedback="Only feedback")  # Missing comment

    with pytest.raises(ValidationError):
        FeedbackRequest(comment="Only comment")  # Missing feedback
