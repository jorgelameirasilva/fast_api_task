#!/usr/bin/env python3
"""
Super simple SYNCHRONOUS example of using the CosmosService
No asyncio, no await - just regular Python functions
"""

from datetime import datetime
from app.services.cosmos_service import CosmosService
from app.models.chat import ChatMessage


def main():
    print("🚀 Simple Synchronous CosmosService Example")
    print("=" * 50)

    # Create service with hardcoded connection
    service = CosmosService(
        connection_string="mongodb://localhost:27017/",
        database_name="sync_example",
        collection_name="sync_sessions",
    )

    try:
        print("\n1️⃣ Creating a session...")
        # Use the synchronous MongoDB operations directly
        session_id = str(__import__("uuid").uuid4())
        user_id = "jane_doe"

        # Create session document manually
        session_doc = {
            "_id": session_id,
            "user_id": user_id,
            "partition_key": user_id,
            "title": "Sync Chat Session",
            "messages": [],
            "context": {},
            "max_messages": 50,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Insert directly into MongoDB
        service.collection.insert_one(session_doc)
        print(f"✅ Created session: {session_id}")
        print(f"   User: {user_id}")
        print(f"   Title: Sync Chat Session")

        print("\n2️⃣ Adding messages...")
        # Add user message
        user_message = {
            "role": "user",
            "content": "Hello from sync world!",
            "timestamp": datetime.utcnow().isoformat(),
        }

        assistant_message = {
            "role": "assistant",
            "content": "Hi there! I'm responding synchronously!",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Update session with messages
        service.collection.update_one(
            {"_id": session_id, "user_id": user_id},
            {
                "$push": {"messages": {"$each": [user_message, assistant_message]}},
                "$set": {"updated_at": datetime.utcnow().isoformat()},
            },
        )
        print(f"✅ Added user message: {user_message['content']}")
        print(f"✅ Added assistant message: {assistant_message['content']}")
        print(f"   Total messages: 2")

        print("\n3️⃣ Getting the session back...")
        retrieved_doc = service.collection.find_one(
            {"_id": session_id, "user_id": user_id}
        )
        if retrieved_doc:
            print(f"✅ Retrieved session: {retrieved_doc['title']}")
            print(f"   Messages in session: {len(retrieved_doc['messages'])}")
            for i, msg in enumerate(retrieved_doc["messages"], 1):
                print(f"   {i}. [{msg['role']}]: {msg['content']}")

        print("\n4️⃣ Creating another session...")
        session2_id = str(__import__("uuid").uuid4())
        session2_doc = {
            "_id": session2_id,
            "user_id": user_id,
            "partition_key": user_id,
            "title": "Quick Help",
            "messages": [],
            "context": {},
            "max_messages": 50,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        service.collection.insert_one(session2_doc)
        print(f"✅ Created second session: Quick Help")

        print("\n5️⃣ Listing all sessions...")
        sessions_cursor = service.collection.find(
            {"user_id": user_id}, {"messages": 0}  # Exclude messages for summary
        ).sort("updated_at", -1)

        sessions = list(sessions_cursor)
        print(f"✅ Found {len(sessions)} sessions for {user_id}:")
        for session_doc in sessions:
            message_count = len(
                service.collection.find_one(
                    {"_id": session_doc["_id"]}, {"messages": 1}
                ).get("messages", [])
            )
            print(f"   • {session_doc['title']} ({message_count} messages)")

        print("\n6️⃣ Deleting a session...")
        result = service.collection.update_one(
            {"_id": session2_id, "user_id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow().isoformat()}},
        )
        success = result.modified_count > 0
        print(f"✅ Deleted session: {success}")

        # Count active sessions
        active_count = service.collection.count_documents(
            {"user_id": user_id, "is_active": True}
        )
        print(f"   Active sessions now: {active_count}")

        print("\n🎉 All done! Synchronous operations work perfectly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up - drop the test database
        print("\n🧹 Cleaning up...")
        try:
            service.collection.drop()
            print("   Test database cleaned")
        except:
            pass

        # Close connection synchronously
        if hasattr(service, "_client") and service._client:
            service._client.close()
            print("   Connection closed")


if __name__ == "__main__":
    # Just run it - no asyncio needed!
    main()
