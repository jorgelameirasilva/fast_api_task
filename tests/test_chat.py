"""
Simple test for chat endpoint
"""

import json


def test_chat_endpoint(client, sample_chat_request):
    """Test chat endpoint with real request - no mocking"""

    # Make request to chat endpoint
    response = client.post("/chat", json=sample_chat_request)

    # Verify we get a successful response
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json-lines"

    # Parse the NDJSON response
    response_text = response.text.strip()
    lines = response_text.split("\n")
    first_line = lines[0] if lines else ""

    # Remove "data: " prefix if present
    if first_line.startswith("data: "):
        json_str = first_line[6:]
    else:
        json_str = first_line

    # Parse JSON response
    data = json.loads(json_str)

    # Verify response structure
    assert "message" in data
    assert "role" in data["message"]
    assert "content" in data["message"]
    assert data["message"]["role"] == "assistant"
    assert isinstance(data["message"]["content"], str)
    assert len(data["message"]["content"]) > 0
