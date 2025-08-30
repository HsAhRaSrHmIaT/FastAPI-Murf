"""Main FastAPI application"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

from app.core.config import settings, get_all_user_keys, update_user_key
# from app.core.logging import setup_logging, get_logger
from app.api import health
from app.api import search
from websocket_handler import websocket_endpoint

# Setup logging
# setup_logging()
# logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Voice Chat API",
    description="AI-powered real-time voice conversation with speech-to-speech pipeline using streaming LLM responses",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(health.router)
app.include_router(search.router)

# logger.info("AI Voice Chat API initialized successfully")

# WebSocket endpoint using the refactored handler
app.websocket("/ws")(websocket_endpoint)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # logger.info("AI Voice Chat interface requested")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/update-keys")
async def update_keys(request: Request):
    form_data = await request.form()
    assemblyai_api_key: Optional[str] = form_data.get("assemblyai_api_key")
    google_api_key: Optional[str] = form_data.get("google_api_key")
    murf_api_key: Optional[str] = form_data.get("murf_api_key")

    # Update user keys using the utility functions
    if assemblyai_api_key:
        update_user_key("assemblyai_api_key", assemblyai_api_key)
    if google_api_key:
        update_user_key("google_api_key", google_api_key)
    if murf_api_key:
        update_user_key("murf_api_key", murf_api_key)

    return {"message": "API keys saved successfully"}

@app.get("/settings", response_class=HTMLResponse)
async def read_settings(request: Request):
    # logger.info("AI Voice Chat settings requested")
    user_keys = get_all_user_keys()
    return templates.TemplateResponse("settings.html", {"request": request, "user_keys": user_keys})

@app.get("/about", response_class=HTMLResponse)
async def read_about(request: Request):
    # logger.info("AI Voice Chat about page requested")
    return templates.TemplateResponse("about.html", {"request": request})

# @app.on_event("startup")
# async def startup_event():
#     """Application startup event: enforce presence of MASTER_KEY in production.

#     For localhost/dev we allow missing MASTER_KEY to preserve developer
#     convenience. In production (when settings.debug is False) the app will
#     raise RuntimeError so deployments (Railway, Docker, systemd) fail fast and
#     the operator sets the required env var.
#     """
#     # logger.info(f"AI Voice Chat API starting up on {settings.host}:{settings.port}")
#     # logger.info(f"Debug mode: {settings.debug}")
#     from app.core.config import has_master_key

#     if not has_master_key() and not settings.debug:
#         # Fail fast in production if MASTER_KEY is missing
#         raise RuntimeError(
#             "MASTER_KEY is required in production for encrypting user-provided secrets."
#         )

# @app.on_event("shutdown")
# async def shutdown_event():
#     """Application shutdown event"""
#     logger.info("AI Voice Chat API shutting down")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
