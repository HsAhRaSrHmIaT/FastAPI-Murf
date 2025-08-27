"""Main FastAPI application"""
import os
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api import health
from app.api import search
from websocket_handler import websocket_endpoint

# Setup logging
setup_logging()
logger = get_logger(__name__)

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

logger.info("AI Voice Chat API initialized successfully")

# WebSocket endpoint using the refactored handler
app.websocket("/ws")(websocket_endpoint)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info("AI Voice Chat interface requested")
    return templates.TemplateResponse("index.html", {"request": request})

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"AI Voice Chat API starting up on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Log service availability
    from app.services.health_service import health_service
    health_status = health_service.get_health_status()
    logger.info(f"Application health: {health_status.status}")
    if health_status.missing_api_keys:
        logger.warning(f"Missing API keys: {health_status.missing_api_keys}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("AI Voice Chat API shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
