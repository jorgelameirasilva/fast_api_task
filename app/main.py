from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.endpoints import router as api_router
from app.core.config import settings
from app.core.setup import setup_clients, cleanup_clients
from app.exceptions.base import CustomException

# Configure logging
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    format="{time} {level} {message}",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Chat Application API converted from Quart",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize clients and services on startup"""
    logger.info("Application startup initiated")
    try:
        await setup_clients()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup clients during startup: {e}")
        # Don't raise the exception to allow the app to start with mock clients
        logger.warning("Application started with fallback/mock clients")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup clients and resources on shutdown"""
    logger.info("Application shutdown initiated")
    try:
        await cleanup_clients()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


# Exception handlers
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    """Handle custom exceptions"""
    logger.error(f"Custom exception: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={"message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


# Include API routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
