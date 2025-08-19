"""Main FastAPI application"""
import json
import os
from datetime import datetime
from random import sample
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api import health, agent, legacy
from app.services.stt_service import AssemblyAIStreamingTranscriber

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
os.makedirs(f"{settings.upload_dir}/audio", exist_ok=True)  # For audio files

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(f"/{settings.upload_dir}", StaticFiles(directory=settings.upload_dir), name="uploads")

templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(health.router)
app.include_router(agent.router)
app.include_router(legacy.router)

logger.info("Voice Agent API initialized successfully")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    # Send connection confirmation to client
    await websocket.send_text(json.dumps({
        "type": "connection",
        "message": "Connected to voice streaming server"
    }))
    
    transcriber = None
    
    def on_transcript_received(transcript: str, is_final: bool):
        """Callback for when transcript is received"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If the loop is already running, use asyncio.run_coroutine_threadsafe
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": transcript,
                        "is_final": is_final,
                        "timestamp": datetime.now().isoformat()
                    })),
                    loop
                )
            else:
                logger.warning("Event loop is not running")

        except Exception as e:
            logger.error(f"Error sending transcript: {e}")
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    # Handle text commands
                    try:
                        data = json.loads(message["text"])
                        
                        if data.get("command") == "start_recording":
                            logger.info("Starting recording session")
                            transcriber = AssemblyAIStreamingTranscriber(sample_rate=16000)
                            if transcriber.start_streaming(on_transcript_received):
                                await websocket.send_text(json.dumps({
                                    "type": "status",
                                    "message": "Recording started - speak now!"
                                }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "message": "Failed to start transcription service"
                                }))
                        
                        elif data.get("command") == "stop_recording":
                            logger.info("Stopping recording session")
                            if transcriber:
                                transcriber.stop_streaming()
                                transcriber = None
                            await websocket.send_text(json.dumps({
                                "type": "status",
                                "message": "Recording stopped"
                            }))
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                
                elif "bytes" in message:
                    # Handle audio data
                    audio_data = message["bytes"]
                    if transcriber and len(audio_data) > 0:
                        logger.debug(f"Streaming {len(audio_data)} bytes of audio")
                        transcriber.stream_audio(audio_data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if transcriber:
            transcriber.stop_streaming()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info("Main interface requested")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/websocket", response_class=HTMLResponse)
async def websocket_test(request: Request):
    logger.info("WebSocket test interface requested")
    return templates.TemplateResponse("websocket.html", {"request": request})

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
