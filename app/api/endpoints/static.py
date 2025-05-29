import mimetypes
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from loguru import logger

from app.core.config import settings

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    """
    Main index page
    """
    logger.info("Index page accessed")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat Application</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .api-links { background: #f5f5f5; padding: 20px; border-radius: 8px; }
            .api-links h3 { margin-top: 0; }
            .api-links a { display: block; margin: 10px 0; color: #0066cc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Chat Application</h1>
                <p>Welcome to the FastAPI Chat Application</p>
            </div>
            <div class="api-links">
                <h3>API Documentation</h3>
                <a href="/docs">Swagger UI Documentation</a>
                <a href="/redoc">ReDoc Documentation</a>
                <h3>Health Check</h3>
                <a href="/health">Application Health</a>
            </div>
        </div>
    </body>
    </html>
    """


@router.get("/redirect")
async def redirect():
    """
    Redirect endpoint
    """
    logger.info("Redirect endpoint accessed")
    return {"message": "redirect", "status": "success"}


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    logger.info("Health check accessed")
    return {"status": "healthy", "service": "chat-application", "version": "1.0.0"}


@router.get("/favicon.ico")
async def favicon():
    """
    Favicon endpoint
    """
    favicon_path = Path(settings.STATIC_DIR) / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        # Return a default response if favicon doesn't exist
        raise HTTPException(status_code=404, detail="Favicon not found")


@router.get("/assets/{file_path:path}")
async def assets(file_path: str):
    """
    Serve static assets
    """
    logger.info(f"Serving asset: {file_path}")

    # Security check: prevent directory traversal
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    asset_path = Path(settings.STATIC_DIR) / "assets" / file_path

    # Ensure the resolved path is within the assets directory
    try:
        asset_path = asset_path.resolve()
        assets_dir = (Path(settings.STATIC_DIR) / "assets").resolve()
        if not str(asset_path).startswith(str(assets_dir)):
            raise HTTPException(status_code=400, detail="Invalid file path")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    if not asset_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Guess the media type
    media_type, _ = mimetypes.guess_type(str(asset_path))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(asset_path, media_type=media_type)


@router.get("/content/{file_path:path}")
async def content_file(file_path: str):
    """
    Serve content files
    """
    logger.info(f"Serving content file: {file_path}")

    # Security check: prevent directory traversal
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Remove page number from path if present (filename-1.txt -> filename.txt)
    if "#page=" in file_path:
        file_path = file_path.split("#page=")[0]

    content_path = Path(settings.CONTENT_DIR) / file_path

    # Ensure the resolved path is within the content directory
    try:
        content_path = content_path.resolve()
        content_dir = Path(settings.CONTENT_DIR).resolve()
        if not str(content_path).startswith(str(content_dir)):
            raise HTTPException(status_code=400, detail="Invalid file path")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not content_path.exists():
        raise HTTPException(status_code=404, detail="Content file not found")

    if not content_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Guess the media type
    media_type, _ = mimetypes.guess_type(str(content_path))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(content_path, media_type=media_type)
