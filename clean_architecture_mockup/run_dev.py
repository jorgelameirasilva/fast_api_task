#!/usr/bin/env python3
"""
Development Startup Script for Clean Architecture FastAPI Application

This script provides a convenient way to start the application in development mode
with proper environment setup and health checks.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
import requests
from typing import Optional


def check_python_version():
    """Ensure Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(
        f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn

        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please run: pip install -r requirements_v2.txt")
        return False


def setup_environment():
    """Setup development environment variables"""
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    print(f"✅ Environment: {os.environ.get('ENVIRONMENT')}")


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready"""
    print(f"🔄 Waiting for server at {url}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    print(f"❌ Server not ready after {timeout} seconds")
    return False


def print_welcome_message():
    """Print welcome message with useful URLs"""
    print("\n" + "=" * 60)
    print("🚀 Clean Architecture FastAPI Application - Development Mode")
    print("=" * 60)
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Alternative Docs:  http://localhost:8000/redoc")
    print("❤️  Health Check:     http://localhost:8000/v2/health")
    print("ℹ️  API Info:         http://localhost:8000/v2/info")
    print("🏠 Root Endpoint:     http://localhost:8000/")
    print("=" * 60)
    print("💡 Features:")
    print("   • Mock services enabled (no external dependencies)")
    print("   • Hot reload enabled")
    print("   • Comprehensive logging")
    print("   • Health monitoring")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")


def main():
    """Main startup function"""
    print("🏗️  Starting Clean Architecture FastAPI Application...")

    # Pre-flight checks
    check_python_version()

    if not check_dependencies():
        sys.exit(1)

    setup_environment()

    # Print welcome message
    print_welcome_message()

    # Start the server
    try:
        # Use uvicorn directly for better control
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "main_v2:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
            "--log-level",
            "info",
            "--access-log",
        ]

        print("🚀 Starting server...")
        subprocess.run(cmd)

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
