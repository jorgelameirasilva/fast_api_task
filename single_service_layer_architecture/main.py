"""
FastAPI Application - Single Service Layer Architecture
The simplest clean architecture with combined coordination + business logic
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.api.endpoints.chat_endpoints import router as chat_router
from app.api.endpoints.vote_endpoints import router as vote_router


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
    logger.info("🚀 Starting Single Service Layer Architecture API...")

    # Initialize any startup tasks here
    logger.info("✅ Application startup completed")

    yield

    # Shutdown
    logger.info("🛑 Shutting down application...")
    logger.info("✅ Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Single Service Layer Architecture API",
    description="AI Chat API with the simplest clean architecture - single service layer",
    version="1.0.0",
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
    """Root endpoint"""
    return {
        "message": "Single Service Layer Architecture API",
        "version": "1.0.0",
        "architecture": "Single Service Layer - Simplest Clean Architecture",
        "layers": {
            "api": "HTTP endpoints",
            "auth": "Authentication gateway",
            "service": "Combined coordination + business logic",
            "repository": "Data access abstraction",
        },
        "endpoints": {"chat": "/chat/*", "vote": "/vote/*", "docs": "/docs"},
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "architecture": "single_service_layer",
        "layers": {"api": "✅", "auth": "✅", "service": "✅", "repository": "✅"},
        "simplicity": "maximum",
    }


# Include routers
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(vote_router, prefix="/vote", tags=["vote"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
