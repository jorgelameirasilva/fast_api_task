"""Main FastAPI application"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logs import setup_logging
from app.api.routes import chat, vote, session
from app.api.dependencies.auth import get_auth_setup
from app.utils.mock_clients import cleanup_mock_clients

# Setup logging
logger, listener, azure_handler = setup_logging("hr-chatbot.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting HR Chatbot API...")

    # Set use_mock_clients to True for development
    settings.use_mock_clients = True
    logger.info("Using mock clients for development")

    yield

    # Shutdown
    logger.info("Shutting down HR Chatbot API...")

    try:
        # Cleanup mock clients
        await cleanup_mock_clients()

        # Stop logging listeners
        if listener:
            listener.stop()
        if azure_handler:
            azure_handler.close()

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="HR Chatbot API - FastAPI migration with authentication",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
if settings.allowed_origin:
    logger.info(f"CORS enabled for {settings.allowed_origin}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
else:
    # Allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(chat.router, tags=["chat"])
app.include_router(vote.router, tags=["vote"])
app.include_router(session.router, tags=["session"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy", "service": "hr-chatbot-api"}


# Auth setup endpoint (equivalent to original /auth_setup)
@app.get("/auth_setup")
async def auth_setup():
    """Send MSAL.js settings to the client UI"""
    try:
        return JSONResponse(content=get_auth_setup())
    except Exception as e:
        logger.error(f"Failed to get auth setup: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get authentication setup"
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HR Chatbot API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "vote": "/vote",
            "auth_setup": "/auth_setup",
            "health": "/health",
            "docs": "/docs" if settings.debug else "disabled",
        },
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": f"The app encountered an error processing your request. Error type: {type(exc).__name__}"
        },
    )


# Custom validation error handler for consistent error format
@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    """Handle validation errors with consistent format"""
    logger.warning(f"Validation error: {exc}")

    # Extract first error message to match original format
    if hasattr(exc, "detail") and exc.detail:
        if isinstance(exc.detail, list) and len(exc.detail) > 0:
            error_msg = exc.detail[0].get("msg", "Validation error")
        else:
            error_msg = str(exc.detail)
    else:
        error_msg = "Validation error"

    return JSONResponse(status_code=400, content={"error": error_msg})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
