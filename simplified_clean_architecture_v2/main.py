"""
FastAPI Application - Simplified Clean Architecture
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
    logger.info("🚀 Starting Simplified Clean Architecture API...")

    # Initialize any startup tasks here
    logger.info("✅ Application startup completed")

    yield

    # Shutdown
    logger.info("🛑 Shutting down application...")
    logger.info("✅ Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Simplified Clean Architecture API",
    description="AI Chat API with Vote functionality using simplified clean architecture",
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
        "message": "Simplified Clean Architecture API",
        "version": "1.0.0",
        "architecture": "Decoupled Clean Architecture",
        "endpoints": {"chat": "/chat/*", "vote": "/vote/*", "docs": "/docs"},
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "architecture": "simplified_clean_architecture",
        "layers": {
            "api": "✅",
            "auth": "✅",
            "application": "✅",
            "domain": "✅",
            "repository": "✅",
        },
    }


# Include routers
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(vote_router, prefix="/vote", tags=["vote"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
