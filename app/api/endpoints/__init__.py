from fastapi import APIRouter

from app.api.endpoints import chat, static

router = APIRouter()

# Include chat endpoints
router.include_router(chat.router, tags=["chat"])

# Include static file endpoints
router.include_router(static.router, tags=["static"])
