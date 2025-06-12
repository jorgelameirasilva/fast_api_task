"""
Clean Architecture FastAPI Application - V2
Main application setup with dependency injection and clean architecture
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.container import container
from app.api.endpoints.v2_endpoints import router as v2_router
from app import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Clean Architecture FastAPI Application V2")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")

    # Initialize container
    container.wire(modules=["app.api.endpoints.v2_endpoints", "app.core.container"])

    logger.info("Dependency injection container initialized")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    container.unwire()


# Create FastAPI application
app = FastAPI(
    title="Clean Architecture API",
    description="FastAPI application with Clean Architecture and Dependency Injection",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(v2_router)


@app.get("/")
async def root():
    """Root endpoint with application information"""
    return {
        "message": "Clean Architecture FastAPI Application",
        "version": __version__,
        "architecture": "Clean Architecture with Dependency Injection",
        "documentation": "/docs",
        "api_info": "/v2/info",
        "health_check": "/v2/health",
    }


@app.get("/health")
async def simple_health():
    """Simple health check for load balancers"""
    return {"status": "healthy", "version": __version__}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Development server configuration
    uvicorn.run("main_v2:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
