"""FastAPI HR Chatbot Application"""

import logging
import mimetypes
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, vote
from app.api.dependencies.auth import auth_helper, require_jwt_auth, get_auth_claims
from app.core.config import settings
from app.utils.exceptions import AppException


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix Windows registry mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Use mock clients: {settings.use_mock_clients}")
    logger.info(f"Authentication enabled: {settings.azure_use_authentication}")

    # Initialize authentication
    if settings.azure_use_authentication:
        logger.info(f"JWT Issuer: {auth_helper.ISSUER}")
        logger.info(f"JWT Audience: {auth_helper.AUDIENCE}")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="HR Chatbot API",
    description="FastAPI-based HR Chatbot with JWT Authentication",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"]
        if settings.debug
        else [settings.allowed_origin] if settings.allowed_origin else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "hr-chatbot-api"}


@app.get("/auth_setup")
async def get_auth_setup():
    """Get authentication setup for client applications"""
    try:
        auth_setup = auth_helper.get_auth_setup_for_client()
        return auth_setup
    except Exception as e:
        logger.error(f"Failed to get auth setup: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get authentication setup"
        )


@app.post("/auth/validate")
async def validate_token(token_claims: Dict[str, Any] = Depends(require_jwt_auth)):
    """
    Validate JWT token endpoint

    This endpoint provides detailed JWT token validation including:
    - Token signature verification
    - Expiration checks
    - Issuer validation
    - Audience validation
    - Claims extraction

    Returns the decoded token claims if valid.
    """
    return {"valid": True, "claims": token_claims, "message": "Token is valid"}


@app.get("/auth/claims")
async def get_user_claims(auth_claims: Dict[str, Any] = Depends(get_auth_claims)):
    """
    Get user authentication claims

    This endpoint returns the current user's authentication claims
    including user ID, groups, email, etc.
    """
    return {"authenticated": bool(auth_claims), "claims": auth_claims}


@app.get("/auth/profile")
async def get_user_profile(token_claims: Dict[str, Any] = Depends(require_jwt_auth)):
    """
    Get authenticated user profile

    This endpoint requires valid JWT authentication and returns
    detailed user profile information from the token claims.
    """
    user_profile = {
        "user_id": token_claims.get("oid") or token_claims.get("sub"),
        "name": token_claims.get("name"),
        "email": token_claims.get("email") or token_claims.get("upn"),
        "groups": token_claims.get("groups", []),
        "tenant_id": token_claims.get("tid"),
        "issued_at": token_claims.get("iat"),
        "expires_at": token_claims.get("exp"),
        "issuer": token_claims.get("iss"),
        "audience": token_claims.get("aud"),
    }

    return {"authenticated": True, "profile": user_profile}


# Include API routes
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(vote.router, prefix="/vote", tags=["vote"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
    )
