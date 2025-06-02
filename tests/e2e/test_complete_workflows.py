import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock


class TestCompleteWorkflows:
    """End-to-end tests for complete user workflows"""

    def test_complete_chat_conversation_workflow(self, client):
        """Test a complete multi-turn chat conversation"""
        session_id = "e2e-test-session"

        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            # Mock different responses for each turn
            responses = [
                ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content="Hello! How can I help you?",
                        timestamp=datetime.now(),
                    ),
                    session_state=session_id,
                    context={"approach_used": "ChatApproach"},
                ),
                ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content="AI is artificial intelligence, a field of computer science.",
                        timestamp=datetime.now(),
                    ),
                    session_state=session_id,
                    context={"approach_used": "ChatApproach"},
                ),
                ChatResponse(
                    message=ChatMessage(
                        role="assistant",
                        content="AI applications include robotics, natural language processing, and machine learning.",
                        timestamp=datetime.now(),
                    ),
                    session_state=session_id,
                    context={"approach_used": "ChatApproach"},
                ),
            ]

            # Set up side effect to return different responses for each call
            mock_process_chat.side_effect = responses

            # Turn 1: Initial greeting
            response1 = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "session_state": session_id,
                },
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["session_state"] == session_id
            assert "Hello! How can I help you?" in data1["message"]["content"]

            # Turn 2: Ask about AI
            response2 = client.post(
                "/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hello! How can I help you?"},
                        {"role": "user", "content": "What is AI?"},
                    ],
                    "session_state": session_id,
                },
            )

            assert response2.status_code == 200
            data2 = response2.json()
            assert "artificial intelligence" in data2["message"]["content"]

            # Turn 3: Ask for examples
            response3 = client.post(
                "/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hello! How can I help you?"},
                        {"role": "user", "content": "What is AI?"},
                        {
                            "role": "assistant",
                            "content": "AI is artificial intelligence...",
                        },
                        {"role": "user", "content": "What are some applications?"},
                    ],
                    "session_state": session_id,
                },
            )

            assert response3.status_code == 200
            data3 = response3.json()
            assert "applications" in data3["message"]["content"]

    def test_ask_and_vote_workflow(self, client):
        """Test asking a question and then voting on the response"""
        user_query = "How does machine learning work?"

        with patch(
            "app.api.endpoints.chat.chat_service.process_ask"
        ) as mock_process_ask:
            from app.schemas.chat import AskResponse

            mock_response = AskResponse(
                user_query=user_query,
                chatbot_response="Machine learning works by training algorithms on data to make predictions.",
                sources=[
                    {
                        "title": "ML Guide",
                        "url": "/ml-guide.pdf",
                        "relevance_score": 0.95,
                    }
                ],
                context={"confidence": 0.9, "approach_used": "AskApproach"},
                count=0,
            )
            mock_process_ask.return_value = mock_response

            # Step 1: Ask the question
            ask_response = client.post("/ask", json={"user_query": user_query})

            assert ask_response.status_code == 200
            ask_data = ask_response.json()
            chatbot_response = ask_data["chatbot_response"]
            assert "Machine learning works" in chatbot_response
            assert len(ask_data["sources"]) == 1

            # Step 2: Vote on the response (upvote)
            vote_response = client.post(
                "/vote",
                json={
                    "user_query": user_query,
                    "chatbot_response": chatbot_response,
                    "upvote": True,
                    "count": 1,
                    "reason_multiple_choice": "helpful",
                    "additional_comments": "Great explanation!",
                },
            )

            assert vote_response.status_code == 200
            vote_data = vote_response.json()
            assert vote_data["status"] == "success"
            assert vote_data["upvote"] is True

    def test_auth_setup_and_chat_workflow(self, client):
        """Test checking auth setup before engaging in chat"""
        # Step 1: Check auth setup
        auth_response = client.get("/auth_setup")

        assert auth_response.status_code == 200
        auth_data = auth_response.json()
        assert "auth_enabled" in auth_data

        # Step 2: Proceed with chat based on auth status
        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "AuthenticatedChatApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "I can help you with your authenticated session.",
                    "sources": [],
                    "context": {"authenticated": auth_data["auth_enabled"]},
                }
            )
            mock_get_approach.return_value = mock_approach

            chat_response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "I need help"}],
                    "context": {"auth_checked": True},
                },
            )

            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert "help you" in chat_data["message"]["content"]

    def test_error_recovery_workflow(self, client):
        """Test error recovery in a workflow"""
        # Step 1: Try an operation that might fail
        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            # First attempt fails
            mock_approach = Mock()
            mock_approach.name = "FailingApproach"
            mock_approach.run = AsyncMock(
                side_effect=Exception("Service temporarily unavailable")
            )
            mock_get_approach.return_value = mock_approach

            response1 = client.post(
                "/chat", json={"messages": [{"role": "user", "content": "Help me"}]}
            )

            assert response1.status_code == 200
            data1 = response1.json()
            # Should get fallback response
            assert data1["context"]["fallback_used"] is True

        # Step 2: Retry with recovery
        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            # Second attempt succeeds
            mock_approach = Mock()
            mock_approach.name = "RecoveredApproach"
            mock_approach.run = AsyncMock(
                return_value={
                    "content": "I'm back online and ready to help!",
                    "sources": [],
                    "context": {"recovered": True},
                }
            )
            mock_get_approach.return_value = mock_approach

            response2 = client.post(
                "/chat", json={"messages": [{"role": "user", "content": "Try again"}]}
            )

            assert response2.status_code == 200
            data2 = response2.json()
            assert "back online" in data2["message"]["content"]
            assert "fallback_used" not in data2["context"]

    def test_streaming_conversation_workflow(self, client):
        """Test a conversation workflow with streaming responses"""

        async def mock_stream_1():
            yield {"content": "Let me think about that...", "sources": []}

        async def mock_stream_2():
            yield {
                "content": "Based on your previous question, here's more detail...",
                "sources": [],
            }

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "StreamingApproach"
            mock_get_approach.return_value = mock_approach

            # First streaming response
            mock_approach.run = AsyncMock(return_value=mock_stream_1())
            response1 = client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "Tell me about AI"}]},
                params={"stream": True},
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["context"]["streaming"] is True
            assert "think about that" in data1["message"]["content"]

            # Second streaming response
            mock_approach.run = AsyncMock(return_value=mock_stream_2())
            response2 = client.post(
                "/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Tell me about AI"},
                        {"role": "assistant", "content": "Let me think about that..."},
                        {"role": "user", "content": "Can you elaborate?"},
                    ]
                },
                params={"stream": True},
            )

            assert response2.status_code == 200
            data2 = response2.json()
            assert "more detail" in data2["message"]["content"]

    def test_mixed_ask_chat_workflow(self, client):
        """Test workflow mixing ask and chat operations"""
        # Step 1: Start with an ask operation
        with patch("app.services.ask_service.get_best_approach") as mock_get_ask:
            mock_ask_approach = Mock()
            mock_ask_approach.name = "DocumentSearchApproach"
            mock_ask_approach.run = AsyncMock(
                return_value={
                    "content": "According to our documentation, the answer is...",
                    "sources": [{"title": "Official Docs", "url": "/docs.pdf"}],
                    "context": {"search_performed": True},
                }
            )
            mock_get_ask.return_value = mock_ask_approach

            ask_response = client.post(
                "/ask", json={"user_query": "What is the official policy?"}
            )

            assert ask_response.status_code == 200
            ask_data = ask_response.json()
            official_answer = ask_data["chatbot_response"]

        # Step 2: Follow up with chat for clarification
        with patch("app.services.chat_service.get_best_approach") as mock_get_chat:
            mock_chat_approach = Mock()
            mock_chat_approach.name = "FollowUpChatApproach"
            mock_chat_approach.run = AsyncMock(
                return_value={
                    "content": "Let me clarify that policy for you...",
                    "sources": [],
                    "context": {"follow_up": True},
                }
            )
            mock_get_chat.return_value = mock_chat_approach

            chat_response = client.post(
                "/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "What is the official policy?"},
                        {"role": "assistant", "content": official_answer},
                        {"role": "user", "content": "Can you clarify section 3?"},
                    ]
                },
            )

            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert "clarify" in chat_data["message"]["content"]

    def test_feedback_loop_workflow(self, client):
        """Test complete feedback loop workflow"""
        query = "How do I reset my password?"

        # Step 1: Get initial response
        with patch(
            "app.api.endpoints.chat.chat_service.process_ask"
        ) as mock_process_ask:
            from app.schemas.chat import AskResponse

            mock_response = AskResponse(
                user_query=query,
                chatbot_response="To reset your password, go to the login page and click 'Forgot Password'.",
                sources=[{"title": "Help Guide", "url": "/help.pdf"}],
                context={"approach_used": "PasswordResetApproach"},
                count=0,
            )
            mock_process_ask.return_value = mock_response

            initial_response = client.post("/ask", json={"user_query": query})
            initial_data = initial_response.json()
            chatbot_response = initial_data["chatbot_response"]

        # Step 2: User finds response unhelpful and downvotes
        downvote_response = client.post(
            "/vote",
            json={
                "user_query": query,
                "chatbot_response": chatbot_response,
                "upvote": False,
                "count": 1,
                "reason_multiple_choice": "not_helpful",
                "additional_comments": "The steps are unclear",
            },
        )

        assert downvote_response.status_code == 200
        assert downvote_response.json()["upvote"] is False

        # Step 3: User asks follow-up question
        with patch(
            "app.api.endpoints.chat.chat_service.process_chat"
        ) as mock_process_chat:
            from app.schemas.chat import ChatResponse, ChatMessage
            from datetime import datetime

            mock_response = ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content="I understand the previous instructions were unclear. Let me provide step-by-step guidance...",
                    timestamp=datetime.now(),
                ),
                context={
                    "improved_response": True,
                    "approach_used": "ImprovedHelpApproach",
                },
            )
            mock_process_chat.return_value = mock_response

            followup_response = client.post(
                "/chat",
                json={
                    "messages": [
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": chatbot_response},
                        {
                            "role": "user",
                            "content": "That's not clear enough. Can you give me detailed steps?",
                        },
                    ]
                },
            )

            improved_data = followup_response.json()
            assert "step-by-step" in improved_data["message"]["content"]

        # Step 4: User upvotes the improved response
        final_vote_response = client.post(
            "/vote",
            json={
                "user_query": "Detailed password reset steps",
                "chatbot_response": improved_data["message"]["content"],
                "upvote": True,
                "count": 1,
                "reason_multiple_choice": "very_helpful",
                "additional_comments": "Much better explanation!",
            },
        )

        assert final_vote_response.status_code == 200
        assert final_vote_response.json()["upvote"] is True

    def test_session_persistence_workflow(self, client):
        """Test session persistence across multiple interactions"""
        session_id = "persistent-session-test"

        with patch("app.services.chat_service.get_best_approach") as mock_get_approach:
            mock_approach = Mock()
            mock_approach.name = "PersistentApproach"
            mock_get_approach.return_value = mock_approach

            # Multiple interactions with the same session
            interactions = [
                ("Hello", "Hello! I'm here to help."),
                ("What's the weather?", "I don't have access to weather data."),
                ("Thanks anyway", "You're welcome! Anything else?"),
            ]

            for i, (user_msg, expected_response) in enumerate(interactions):
                mock_approach.run = AsyncMock(
                    return_value={
                        "content": expected_response,
                        "sources": [],
                        "context": {"interaction_count": i + 1},
                    }
                )

                # Build message history
                messages = []
                for j in range(i + 1):
                    messages.append({"role": "user", "content": interactions[j][0]})
                    if j < i:  # Don't add assistant response for current turn
                        messages.append(
                            {"role": "assistant", "content": interactions[j][1]}
                        )

                response = client.post(
                    "/chat", json={"messages": messages, "session_state": session_id}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["session_state"] == session_id
                assert expected_response in data["message"]["content"]
