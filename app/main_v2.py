"""
FastAPI Application V2 - Using Clean Architecture with Dependency Injection.
This is the main application file using the new improved architecture.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger

from app.core.config import settings
from app.core.container import initialize_container, container
from app.api.endpoints.chat_endpoints_v2 import router as chat_router_v2


# Configure logging
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting FastAPI application with Clean Architecture V2...")

    try:
        # Initialize dependency injection container
        initialize_container()
        logger.info("✅ Dependency injection container initialized")

        # Test container health
        from app.core.container import check_search_health, check_llm_health

        search_ok = await check_search_health()
        llm_ok = await check_llm_health()

        logger.info(
            f"🔍 Search repository: {'✅ Healthy' if search_ok else '⚠️ Degraded'}"
        )
        logger.info(f"🤖 LLM repository: {'✅ Healthy' if llm_ok else '⚠️ Degraded'}")

        if not search_ok:
            logger.warning(
                "Search repository is not healthy - using mock implementation"
            )
        if not llm_ok:
            logger.warning("LLM repository is not healthy - using mock implementation")

        logger.info("🚀 Application startup completed successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    logger.info("✅ Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Ascendion AI Assistant API V2",
    description="AI-powered assistant with Clean Architecture and Dependency Injection",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    """Application health check endpoint"""
    from app.core.container import check_search_health, check_llm_health

    try:
        search_health = await check_search_health()
        llm_health = await check_llm_health()

        overall_status = "healthy" if search_health and llm_health else "degraded"

        return {
            "status": overall_status,
            "version": "2.0.0",
            "architecture": "clean_architecture_with_ddd",
            "services": {
                "search_repository": "healthy" if search_health else "degraded",
                "llm_repository": "healthy" if llm_health else "degraded",
            },
            "environment": settings.ENVIRONMENT,
            "features": {
                "dependency_injection": True,
                "repository_pattern": True,
                "domain_services": True,
                "orchestration_services": True,
                "mock_fallbacks": True,
            },
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service health check failed")


@app.get("/info")
async def application_info():
    """Application information endpoint"""
    return {
        "application": "Ascendion AI Assistant API",
        "version": "2.0.0",
        "architecture": {
            "pattern": "Clean Architecture with Domain-Driven Design",
            "layers": [
                "Presentation Layer (FastAPI Routers)",
                "Application Layer (Orchestration Services)",
                "Domain Layer (Domain Services)",
                "Infrastructure Layer (Repositories)",
            ],
            "design_patterns": [
                "Dependency Injection",
                "Repository Pattern",
                "Service Layer Pattern",
                "Factory Pattern",
                "Strategy Pattern",
            ],
        },
        "features": {
            "ai_powered_responses": True,
            "document_search": True,
            "conversation_context": True,
            "streaming_responses": True,
            "health_monitoring": True,
            "error_handling": True,
            "mock_fallbacks": True,
        },
        "endpoints": {
            "ask": "/v2/ask",
            "ask_stream": "/v2/ask/stream",
            "chat": "/v2/chat",
            "health": "/v2/health",
            "architecture_info": "/v2/architecture/info",
        },
    }


# Include routers
app.include_router(chat_router_v2)


# Add legacy compatibility if needed
@app.get("/legacy/compatibility")
async def legacy_compatibility():
    """Information about legacy compatibility"""
    return {
        "message": "This is the V2 Clean Architecture implementation",
        "legacy_endpoints": "Available but deprecated",
        "migration_guide": "Use /v2/* endpoints for the new architecture",
        "benefits": [
            "Better testability",
            "Improved maintainability",
            "Cleaner separation of concerns",
            "Production-ready error handling",
            "Dependency injection",
            "Repository pattern abstraction",
        ],
    }


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error(f"ValueError: {exc}")
    return {"error": "Invalid input", "detail": str(exc)}


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {"error": "Internal server error", "detail": "Please contact support"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server with uvicorn...")
    uvicorn.run(
        "app.main_v2:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
