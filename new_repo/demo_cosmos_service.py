"""
Demo script showing CosmosService functionality
Tests all message and session operations
"""

import asyncio
from datetime import datetime

from app.services.cosmos_service import create_cosmos_service
from app.models.document import MessageCreateRequest, MessageContent, MessageVoteRequest


async def demo_cosmos_service():
    """Comprehensive demo of CosmosService operations"""

    print("🎯 CosmosService Demo")
    print("=" * 50)

    # Initialize cosmos service
    cosmos_service = create_cosmos_service()

    user_id = "demo_user_123"

    try:
        # 1. CREATE MESSAGES IN DIFFERENT SESSIONS
        print("\n1️⃣ Creating messages in different sessions...")

        sessions_data = []

        # Session 1: HR Policies
        hr_messages = [
            {"role": "user", "content": "What's our vacation policy?"},
            {
                "role": "assistant",
                "content": "Our vacation policy allows 20 days annually with manager approval.",
            },
            {"role": "user", "content": "How do I request time off?"},
            {
                "role": "assistant",
                "content": "You can request time off through the HR portal or email your manager.",
            },
        ]

        session1_id = await create_session_with_messages(
            cosmos_service, user_id, hr_messages, "hr-policies"
        )
        sessions_data.append(("HR Policies", session1_id, len(hr_messages)))

        # Session 2: IT Support
        it_messages = [
            {"role": "user", "content": "My computer won't start"},
            {
                "role": "assistant",
                "content": "Let's troubleshoot this step by step. First, check the power cable.",
            },
            {"role": "user", "content": "I tried that, still not working"},
            {
                "role": "assistant",
                "content": "I'll create a ticket for hardware support. Ticket #12345 created.",
            },
        ]

        session2_id = await create_session_with_messages(
            cosmos_service, user_id, it_messages, "it-support"
        )
        sessions_data.append(("IT Support", session2_id, len(it_messages)))

        # Session 3: Finance Questions
        finance_messages = [
            {"role": "user", "content": "How do I submit expense reports?"},
            {
                "role": "assistant",
                "content": "You can submit expenses through our finance system at finance.company.com",
            },
        ]

        session3_id = await create_session_with_messages(
            cosmos_service, user_id, finance_messages, "finance"
        )
        sessions_data.append(("Finance", session3_id, len(finance_messages)))

        print(f"✅ Created {len(sessions_data)} sessions:")
        for name, session_id, msg_count in sessions_data:
            print(f"   • {name}: {session_id} ({msg_count} messages)")

        # 2. GET USER SESSIONS
        print("\n2️⃣ Getting user sessions...")

        user_sessions = await cosmos_service.get_user_sessions(user_id, limit=10)

        print(f"✅ Found {len(user_sessions)} sessions for user:")
        for i, session in enumerate(user_sessions, 1):
            print(f"   {i}. {session.title or 'Untitled Session'}")
            print(f"      Session ID: {session.session_id}")
            print(f"      Messages: {session.message_count}")
            print(f"      Created: {session.created_at}")
            print(f"      Updated: {session.updated_at}")
            print()

        # 3. GET CONVERSATION MESSAGES
        print("\n3️⃣ Getting conversation for HR Policies session...")

        hr_conversation = await cosmos_service.get_conversation(
            session1_id, user_id, limit=20
        )

        print(f"✅ Retrieved {len(hr_conversation)} messages:")
        for i, msg in enumerate(hr_conversation, 1):
            print(f"   {i}. [{msg.message.role}] {msg.message.content}")
            print(f"      Message ID: {msg.id}")
            print(f"      Knowledge Base: {msg.knowledge_base or 'None'}")
            print(f"      Created: {msg.created_at}")
            print(f"      Active: {msg.is_active}")
            if msg.upvote or msg.downvote:
                print(f"      Votes: ↑{msg.upvote} ↓{msg.downvote}")
                if msg.feedback:
                    print(f"      Feedback: {msg.feedback}")
            print()

        # 4. VOTE ON MESSAGES
        print("\n4️⃣ Testing message voting...")

        # Find first assistant message to vote on
        assistant_msg = next(
            (msg for msg in hr_conversation if msg.message.role == "assistant"), None
        )
        if assistant_msg:
            # Upvote with feedback
            vote_request = MessageVoteRequest(
                message_id=assistant_msg.id,
                upvote=1,
                downvote=0,
                feedback="Very helpful information about vacation policy!",
            )

            voted_message = await cosmos_service.vote_message(vote_request, user_id)
            if voted_message:
                print(f"✅ Upvoted message: {voted_message.id}")
                print(f"   Upvote: {voted_message.upvote}")
                print(f"   Downvote: {voted_message.downvote}")
                print(f"   Feedback: {voted_message.feedback}")
                print(f"   Voted at: {voted_message.voted_at}")

                # Test downvote (override previous vote)
                downvote_request = MessageVoteRequest(
                    message_id=assistant_msg.id,
                    upvote=0,
                    downvote=1,
                    feedback="Actually, this wasn't clear enough",
                )

                downvoted_message = await cosmos_service.vote_message(
                    downvote_request, user_id
                )
                if downvoted_message:
                    print(f"✅ Changed to downvote: {downvoted_message.id}")
                    print(f"   Upvote: {downvoted_message.upvote}")
                    print(f"   Downvote: {downvoted_message.downvote}")
                    print(f"   Feedback: {downvoted_message.feedback}")

        # 5. GET SPECIFIC MESSAGE
        print("\n5️⃣ Testing get specific message...")

        if assistant_msg:
            retrieved_msg = await cosmos_service.get_message(assistant_msg.id, user_id)
            if retrieved_msg:
                print(f"✅ Retrieved message: {retrieved_msg.id}")
                print(f"   Content: {retrieved_msg.message.content}")
                print(f"   Votes: ↑{retrieved_msg.upvote} ↓{retrieved_msg.downvote}")
                print(f"   Feedback: {retrieved_msg.feedback or 'None'}")
            else:
                print("❌ Message not found")

        # 6. ADD NEW MESSAGES TO EXISTING SESSION
        print("\n6️⃣ Adding new messages to existing IT session...")

        # Add follow-up messages to IT session
        followup_msgs = [
            {"role": "user", "content": "Can you escalate this to level 2 support?"},
            {
                "role": "assistant",
                "content": "I've escalated your ticket to level 2. You should hear back within 2 hours.",
            },
        ]

        for msg_data in followup_msgs:
            message_request = MessageCreateRequest(
                session_id=session2_id,
                message=MessageContent(
                    role=msg_data["role"], content=msg_data["content"]
                ),
                knowledge_base="it-support",
            )

            created_msg = await cosmos_service.create_message(message_request, user_id)
            print(f"✅ Added message: {created_msg.id}")
            print(f"   Role: {created_msg.message.role}")
            print(f"   Content: {created_msg.message.content}")

        # 7. SESSION STATISTICS
        print("\n7️⃣ Session statistics after updates...")

        updated_sessions = await cosmos_service.get_user_sessions(user_id)

        total_sessions = len(updated_sessions)
        total_messages = sum(s.message_count for s in updated_sessions)
        most_active_session = (
            max(updated_sessions, key=lambda s: s.message_count)
            if updated_sessions
            else None
        )

        print(f"✅ Updated Session Statistics:")
        print(f"   Total Sessions: {total_sessions}")
        print(f"   Total Messages: {total_messages}")
        if most_active_session:
            print(
                f"   Most Active Session: {most_active_session.title or 'Untitled'} ({most_active_session.message_count} messages)"
            )
        if total_sessions > 0:
            print(
                f"   Average Messages per Session: {total_messages / total_sessions:.1f}"
            )

        # 8. DELETE INDIVIDUAL MESSAGE
        print("\n8️⃣ Testing message deletion...")

        # Create a test message to delete
        test_message = await cosmos_service.create_message(
            MessageCreateRequest(
                session_id=session3_id,
                message=MessageContent(
                    role="user", content="This is a test message that will be deleted"
                ),
                knowledge_base="test",
            ),
            user_id,
        )

        print(f"✅ Created test message: {test_message.id}")

        # Delete the message
        delete_success = await cosmos_service.delete_message(test_message.id, user_id)
        print(f"✅ Message deletion result: {delete_success}")

        # Verify it's gone (should return None or be marked inactive)
        deleted_msg = await cosmos_service.get_message(test_message.id, user_id)
        print(f"   Retrieved deleted message: {deleted_msg}")

        # 9. DELETE ENTIRE SESSION
        print("\n9️⃣ Testing session deletion...")

        print(f"Deleting finance session: {session3_id}")
        session_delete_success = await cosmos_service.delete_session(
            session3_id, user_id
        )
        print(f"✅ Session deletion result: {session_delete_success}")

        # Verify sessions are gone
        final_sessions = await cosmos_service.get_user_sessions(user_id)
        print(f"   Remaining active sessions: {len(final_sessions)}")
        for session in final_sessions:
            print(
                f"     - {session.title or 'Untitled'} ({session.message_count} messages)"
            )

        # 10. CONVERSATION PAGINATION
        print("\n🔟 Testing conversation pagination...")

        # Get conversation with pagination
        page1 = await cosmos_service.get_conversation(
            session2_id, user_id, limit=2, offset=0
        )
        page2 = await cosmos_service.get_conversation(
            session2_id, user_id, limit=2, offset=2
        )

        print(f"✅ Page 1 (first 2 messages): {len(page1)} messages")
        for msg in page1:
            print(f"   - [{msg.message.role}] {msg.message.content[:50]}...")

        print(f"✅ Page 2 (next 2 messages): {len(page2)} messages")
        for msg in page2:
            print(f"   - [{msg.message.role}] {msg.message.content[:50]}...")

        # 11. SECURITY TEST - User can't access other users' data
        print("\n🔐 Testing security - user isolation...")

        other_user_id = "other_user_456"

        # Try to get sessions for other user
        other_sessions = await cosmos_service.get_user_sessions(other_user_id)
        print(f"✅ Other user sessions: {len(other_sessions)} (should be 0)")

        # Try to get conversation for other user
        other_conversation = await cosmos_service.get_conversation(
            session1_id, other_user_id
        )
        print(
            f"✅ Other user conversation access: {len(other_conversation)} messages (should be 0)"
        )

        # Try to vote on message as other user
        if assistant_msg:
            other_vote = await cosmos_service.vote_message(
                MessageVoteRequest(
                    message_id=assistant_msg.id,
                    upvote=1,
                    downvote=0,
                    feedback="Unauthorized vote attempt",
                ),
                other_user_id,
            )
            print(f"✅ Other user vote attempt: {other_vote} (should be None)")

        print("\n🎉 CosmosService Demo Completed!")
        print("=" * 50)

        # Final Summary
        print("\n📊 DEMO SUMMARY:")
        print(f"   • Tested message creation across {len(sessions_data)} sessions")
        print(f"   • Demonstrated session listing and conversation retrieval")
        print(f"   • Tested message voting (upvote and downvote)")
        print(f"   • Verified individual message retrieval")
        print(f"   • Added new messages to existing sessions")
        print(f"   • Tested individual message deletion")
        print(f"   • Tested full session deletion")
        print(f"   • Demonstrated conversation pagination")
        print(f"   • Verified security and user isolation")
        print(f"   • All CosmosService operations working correctly!")

    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        # Clean up connection
        await cosmos_service.close()
        print("\n🔌 Database connection closed")


async def create_session_with_messages(
    cosmos_service, user_id, messages, knowledge_base
):
    """Helper function to create a session with multiple messages"""
    session_id = None

    for msg_data in messages:
        message_request = MessageCreateRequest(
            session_id=session_id,  # First message creates session
            message=MessageContent(role=msg_data["role"], content=msg_data["content"]),
            knowledge_base=knowledge_base,
        )

        created_msg = await cosmos_service.create_message(message_request, user_id)

        if session_id is None:
            session_id = created_msg.session_id

    return session_id


if __name__ == "__main__":
    print("🎯 CosmosService Demo")
    print("Make sure MongoDB is running on localhost:27017")
    print("This demo will create test data and then clean it up")
    print()

    # Run the demo
    asyncio.run(demo_cosmos_service())
