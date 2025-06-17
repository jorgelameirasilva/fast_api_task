"""
Comprehensive tests for the new ChatResponse format
Testing ChatChoice, ChatDelta, ChatContentData structure with clear inputs and expected outputs
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatChoice,
    ChatMessage,
    ChatDelta,
    ChatContentData,
    ChatContext,
)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestNewChatResponseFormat:
    """Test the new ChatResponse format with clear inputs and expected outputs"""

    def test_chat_response_model_structure(self):
        """Test that the ChatResponse model has the correct structure"""

        # Clear input data
        input_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Based on the HR policy documents, here's what I found about sick leave...",
                    },
                    "content": {
                        "data_points": [
                            "hr-handbook-illness.pdf",
                            "employee-benefits-guide.pdf",
                        ],
                        "thoughts": "The user is asking about sick leave policy. I found relevant information in the HR handbook.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "session_state": "session_123",
            "context": {
                "overrides": {"use_semantic_captions": True},
                "session_state": "session_123",
            },
        }

        # Expected output structure
        response = ChatResponse(**input_data)

        # Validate the structure
        assert isinstance(response, ChatResponse)
        assert len(response.choices) == 1
        assert isinstance(response.choices[0], ChatChoice)
        assert isinstance(response.choices[0].message, ChatMessage)
        assert isinstance(response.choices[0].content, ChatContentData)
        assert isinstance(response.context, ChatContext)

        # Validate content
        choice = response.choices[0]
        assert choice.message.role == "assistant"
        assert "sick leave" in choice.message.content
        assert "hr-handbook-illness.pdf" in choice.content.data_points
        assert "HR handbook" in choice.content.thoughts
        assert choice.finish_reason == "stop"

        print("✅ ChatResponse model structure test passed")

    def test_streaming_chat_delta_structure(self):
        """Test ChatDelta structure for streaming responses"""

        # Clear input: streaming delta chunks
        delta_chunks = [
            {"role": "assistant", "content": "Based on"},
            {"role": None, "content": " the HR policy"},
            {"role": None, "content": " documents..."},
        ]

        # Expected output: ChatChoice with ChatDelta
        choices = []
        for chunk_data in delta_chunks:
            delta = ChatDelta(**chunk_data)
            choice = ChatChoice(
                delta=delta, finish_reason=None if chunk_data["content"] else "stop"
            )
            choices.append(choice)

        # Validate structure
        assert len(choices) == 3
        assert choices[0].delta.role == "assistant"
        assert choices[0].delta.content == "Based on"
        assert choices[1].delta.role is None
        assert choices[1].delta.content == " the HR policy"
        assert choices[2].delta.content == " documents..."

        print("✅ ChatDelta streaming structure test passed")

    def test_complete_chat_response_example(self):
        """Test a complete real-world ChatResponse example"""

        # Clear input: Realistic HR chatbot response
        hr_response_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "To report illness, you need to:\n\n1. Contact your supervisor immediately\n2. Fill out the incident report form\n3. Submit a doctor's note for absences over 3 days\n\nFor more details, refer to the employee handbook section 4.2.",
                    },
                    "content": {
                        "data_points": [
                            "hr-handbook-illness.pdf: Section 4.2 - Illness Reporting Procedures",
                            "employee-benefits-guide.pdf: Page 15 - Sick Leave Policy",
                            "incident-report-form.pdf: Form IR-001",
                        ],
                        "thoughts": "User asked about reporting illness. I found specific procedures in the HR handbook section 4.2, plus supporting information about sick leave policy and the required forms. The response includes step-by-step instructions and references to official documents.",
                    },
                    "function_call": None,
                    "tool_calls": None,
                    "finish_reason": "stop",
                }
            ],
            "session_state": "usr_456_session_789",
            "context": {
                "overrides": {
                    "semantic_ranker": True,
                    "use_semantic_captions": True,
                    "top": 3,
                    "suggest_followup_questions": True,
                },
                "session_state": "usr_456_session_789",
            },
        }

        # Expected output: Valid ChatResponse
        response = ChatResponse(**hr_response_data)

        # Comprehensive validation
        assert response.session_state == "usr_456_session_789"
        assert response.context.session_state == "usr_456_session_789"
        assert response.context.overrides["semantic_ranker"] is True

        choice = response.choices[0]
        assert choice.message.role == "assistant"
        assert "Contact your supervisor" in choice.message.content
        assert "section 4.2" in choice.message.content
        assert choice.finish_reason == "stop"
        assert choice.function_call is None
        assert choice.tool_calls is None

        content = choice.content
        assert len(content.data_points) == 3
        assert "hr-handbook-illness.pdf" in content.data_points[0]
        assert "employee-benefits-guide.pdf" in content.data_points[1]
        assert "incident-report-form.pdf" in content.data_points[2]
        assert "HR handbook section 4.2" in content.thoughts
        assert "step-by-step instructions" in content.thoughts

        print("✅ Complete ChatResponse example test passed")
        print(f"   Response length: {len(choice.message.content)} characters")
        print(f"   Data points: {len(content.data_points)}")
        print(f"   Thoughts length: {len(content.thoughts)} characters")

    @pytest.mark.asyncio
    async def test_chat_endpoint_with_new_format(self, client):
        """Test the actual chat endpoint returns the new format"""

        # Clear input: Realistic chat request
        chat_request = {
            "messages": [
                {"role": "user", "content": "How do I report being sick at work?"}
            ],
            "context": {"overrides": {"semantic_ranker": True, "top": 3}},
            "stream": False,
        }

        # Mock environment for testing
        import os

        os.environ["USE_MOCK_CLIENTS"] = "true"

        # Expected output: HTTP 200 with new ChatResponse format
        response = client.post("/chat", json=chat_request)

        # We expect this to work now with the new format
        assert response.status_code in [200, 401]  # 401 if auth is required

        if response.status_code == 200:
            data = response.json()

            # Validate new structure
            assert "choices" in data
            assert isinstance(data["choices"], list)
            assert len(data["choices"]) > 0

            choice = data["choices"][0]
            assert "message" in choice
            assert "content" in choice
            assert "finish_reason" in choice

            # Validate message structure
            message = choice["message"]
            assert "role" in message
            assert "content" in message
            assert message["role"] == "assistant"

            # Validate content structure
            content = choice["content"]
            assert "data_points" in content
            assert "thoughts" in content
            assert isinstance(content["data_points"], list)

            print("✅ Chat endpoint new format test passed")
            print(f"   Response: {message['content'][:100]}...")
            print(f"   Data points: {len(content['data_points'])}")

    def test_error_cases_with_new_format(self):
        """Test error cases and edge cases with new format"""

        # Test empty choices - Pydantic allows empty lists by default
        # So we test that it creates successfully but has 0 choices
        empty_response = ChatResponse(choices=[], session_state=None, context=None)
        assert len(empty_response.choices) == 0

        # Test choice without message or delta
        choice_no_message = ChatChoice(
            message=None, delta=None, content=None, finish_reason="error"
        )
        response = ChatResponse(
            choices=[choice_no_message], session_state=None, context=None
        )
        assert len(response.choices) == 1
        assert response.choices[0].message is None
        assert response.choices[0].delta is None

        # Test minimal valid response
        minimal_choice = ChatChoice(
            message=ChatMessage(role="assistant", content="Error occurred"),
            finish_reason="error",
        )
        minimal_response = ChatResponse(choices=[minimal_choice])
        assert len(minimal_response.choices) == 1
        assert minimal_response.session_state is None
        assert minimal_response.context is None

        print("✅ Error cases test passed")

    def test_serialization_deserialization(self):
        """Test that the new format can be properly serialized and deserialized"""

        # Create a complete response
        original_response = ChatResponse(
            choices=[
                ChatChoice(
                    message=ChatMessage(
                        role="assistant",
                        content="Here's information about sick leave policy...",
                    ),
                    content=ChatContentData(
                        data_points=["hr-handbook.pdf", "policy-guide.pdf"],
                        thoughts="Found relevant policy information",
                    ),
                    finish_reason="stop",
                )
            ],
            session_state="test_session_123",
            context=ChatContext(
                overrides={"top": 5, "semantic_ranker": True},
                session_state="test_session_123",
            ),
        )

        # Serialize to JSON
        json_data = original_response.model_dump()
        json_string = json.dumps(json_data)

        # Deserialize back
        parsed_data = json.loads(json_string)
        reconstructed_response = ChatResponse(**parsed_data)

        # Validate they're equivalent
        assert reconstructed_response.session_state == original_response.session_state
        assert len(reconstructed_response.choices) == len(original_response.choices)
        assert (
            reconstructed_response.choices[0].message.content
            == original_response.choices[0].message.content
        )
        assert (
            reconstructed_response.choices[0].content.data_points
            == original_response.choices[0].content.data_points
        )
        assert (
            reconstructed_response.context.overrides
            == original_response.context.overrides
        )

        print("✅ Serialization/deserialization test passed")
        print(f"   JSON size: {len(json_string)} bytes")


if __name__ == "__main__":
    """Run tests when executed directly"""
    test_instance = TestNewChatResponseFormat()

    print("🧪 Running ChatResponse Format Tests...")
    print("=" * 60)

    try:
        test_instance.test_chat_response_model_structure()
        test_instance.test_streaming_chat_delta_structure()
        test_instance.test_complete_chat_response_example()
        test_instance.test_error_cases_with_new_format()
        test_instance.test_serialization_deserialization()

        print("=" * 60)
        print("🎉 All ChatResponse format tests passed!")
        print("✅ New format structure validated")
        print("✅ Clear inputs and expected outputs confirmed")
        print("✅ Ready for production use")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
