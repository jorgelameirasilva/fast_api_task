#!/usr/bin/env python3
"""
Super simple example of using the CosmosService directly
No FastAPI, no complex setup - just pure Python
"""

import asyncio
from datetime import datetime
from app.services.cosmos_service import CosmosService
from app.models.chat import ChatMessage


async def main():
    print("🚀 Simple CosmosService Example")
    print("=" * 40)

    # Create service with hardcoded connection
    service = CosmosService(
        connection_string="mongodb://localhost:27017/",
        database_name="simple_example",
        collection_name="my_sessions",
    )

    try:
        print("\n1️⃣ Creating a session...")
        session = await service.create_session(
            user_id="john_doe", title="My First Chat"
        )
        print(f"✅ Created session: {session.id}")
        print(f"   User: {session.user_id}")
        print(f"   Title: {session.title}")

        print("\n2️⃣ Adding messages...")
        # Add user message
        user_msg = ChatMessage(
            role="user",
            content="Hello! How are you today?",
            timestamp=datetime.utcnow(),
        )
        session = await service.add_message(session.id, "john_doe", user_msg)
        print(f"✅ Added user message: {user_msg.content}")

        # Add assistant message
        assistant_msg = ChatMessage(
            role="assistant",
            content="I'm doing great! How can I help you?",
            timestamp=datetime.utcnow(),
        )
        session = await service.add_message(session.id, "john_doe", assistant_msg)
        print(f"✅ Added assistant message: {assistant_msg.content}")

        print(f"   Total messages: {len(session.messages)}")

        print("\n3️⃣ Getting the session back...")
        retrieved = await service.get_session(session.id, "john_doe")
        print(f"✅ Retrieved session: {retrieved.title}")
        print(f"   Messages in session: {len(retrieved.messages)}")
        for i, msg in enumerate(retrieved.messages, 1):
            print(f"   {i}. [{msg.role}]: {msg.content}")

        print("\n4️⃣ Creating another session...")
        session2 = await service.create_session(
            user_id="john_doe", title="Shopping Help"
        )
        print(f"✅ Created second session: {session2.title}")

        print("\n5️⃣ Listing all sessions...")
        sessions = await service.list_sessions("john_doe")
        print(f"✅ Found {len(sessions)} sessions for john_doe:")
        for session_summary in sessions:
            print(
                f"   • {session_summary.title} ({session_summary.message_count} messages)"
            )

        print("\n6️⃣ Deleting a session...")
        success = await service.delete_session(session2.id, "john_doe")
        print(f"✅ Deleted session: {success}")

        # List again to see the change
        active_sessions = await service.list_sessions("john_doe", is_active=True)
        print(f"   Active sessions now: {len(active_sessions)}")

        print("\n🎉 All done! The service works perfectly!")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Clean up - drop the test database
        print("\n🧹 Cleaning up...")
        try:
            service.collection.drop()
            print("   Test database cleaned")
        except:
            pass

        await service.close()
        print("   Connection closed")


if __name__ == "__main__":
    # Just run it!
    asyncio.run(main())
