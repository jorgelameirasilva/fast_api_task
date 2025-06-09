#!/usr/bin/env python3
"""
Startup script for Ascendion AI Assistant API V2
This script starts the new clean architecture implementation.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import loguru
        import dependency_injector

        print("✅ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements_v2.txt")
        return False


def check_optional_dependencies():
    """Check optional dependencies and warn if missing"""
    optional_deps = {
        "openai": "OpenAI integration",
        "azure.search.documents": "Azure Search integration",
        "azure.storage.blob": "Azure Storage integration",
    }

    missing = []
    for dep, description in optional_deps.items():
        try:
            __import__(dep)
            print(f"✅ {description} available")
        except ImportError:
            print(f"⚠️  {description} not available (will use mock implementation)")
            missing.append(dep)

    return missing


def setup_environment():
    """Setup environment variables with defaults"""
    defaults = {
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "INFO",
        "AZURE_USE_AUTHENTICATION": "false",
        "OPENAI_HOST": "standard",  # or "azure"
        "OPENAI_CHATGPT_MODEL": "gpt-3.5-turbo",
        "OPENAI_EMB_MODEL": "text-embedding-ada-002",
        "KB_FIELDS_CONTENT": "content",
        "KB_FIELDS_SOURCEPAGE": "sourcepage",
    }

    for key, default_value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"🔧 Set {key}={default_value}")


async def test_application_health():
    """Test that the application can start and dependencies work"""
    try:
        from app.core.container import (
            initialize_container,
            check_search_health,
            check_llm_health,
        )

        print("🔄 Initializing dependency injection container...")
        initialize_container()
        print("✅ Container initialized successfully")

        print("🔄 Testing repository health...")
        search_ok = await check_search_health()
        llm_ok = await check_llm_health()

        print(f"🔍 Search repository: {'✅ Healthy' if search_ok else '⚠️ Using mock'}")
        print(f"🤖 LLM repository: {'✅ Healthy' if llm_ok else '⚠️ Using mock'}")

        return True

    except Exception as e:
        print(f"❌ Application health check failed: {e}")
        return False


def main():
    """Main startup function"""
    print("🚀 Starting Ascendion AI Assistant API V2")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check optional dependencies
    missing_optional = check_optional_dependencies()

    # Setup environment
    print("\n🔧 Setting up environment...")
    setup_environment()

    # Test application health
    print("\n🏥 Testing application health...")
    if not asyncio.run(test_application_health()):
        print(
            "⚠️  Application health check failed, but continuing with mock implementations"
        )

    # Display configuration
    print("\n📋 Configuration:")
    print(f"   Environment: {os.getenv('ENVIRONMENT')}")
    print(f"   OpenAI Host: {os.getenv('OPENAI_HOST')}")
    print(f"   Model: {os.getenv('OPENAI_CHATGPT_MODEL')}")

    if os.getenv("OPENAI_API_KEY"):
        print("   ✅ OpenAI API Key configured")
    else:
        print("   ⚠️  No OpenAI API Key (using mock LLM)")

    if os.getenv("AZURE_SEARCH_SERVICE"):
        print("   ✅ Azure Search configured")
    else:
        print("   ⚠️  No Azure Search (using mock search)")

    # Show available endpoints
    print("\n🌐 Available Endpoints:")
    print("   📖 Documentation: http://localhost:8000/docs")
    print("   ❓ Ask Question: POST http://localhost:8000/v2/ask")
    print("   💬 Chat: POST http://localhost:8000/v2/chat")
    print("   🩺 Health Check: GET http://localhost:8000/v2/health")
    print("   ℹ️  Architecture Info: GET http://localhost:8000/v2/architecture/info")

    # Start server
    print("\n🚀 Starting FastAPI server...")
    print("=" * 50)

    try:
        import uvicorn

        uvicorn.run(
            "app.main_v2:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
