"""Main FastAPI application"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api import health, agent, legacy

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Voice Agent API",
    description="AI-powered voice interaction platform with speech-to-text, LLM, and text-to-speech capabilities",
    version="2.0.0",
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

# Create upload directory
os.makedirs(settings.upload_dir, exist_ok=True)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(f"/{settings.upload_dir}", StaticFiles(directory=settings.upload_dir), name="uploads")

templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(health.router)
app.include_router(agent.router)
app.include_router(legacy.router)

logger.info("Voice Agent API initialized successfully")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main web interface"""
    logger.info("Main interface requested")
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Voice Agent API starting up on {settings.host}:{settings.port}")
    logger.info(f"Upload directory: {settings.upload_dir}")
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
    logger.info("Voice Agent API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
