"""Main FastAPI application"""
import json
import os
from datetime import datetime
from random import sample
import asyncio
from concurrent.futures import ThreadPoolExecutor
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
    logger.info("WebSocket connected for turn detection")
    
    # Send connection confirmation to client
    await websocket.send_text(json.dumps({
        "type": "connection",
        "message": "Connected to turn detection voice streaming server"
    }))
    
    transcriber = None
    
    # Get the current event loop for thread-safe access
    main_loop = asyncio.get_running_loop()
    
    # Create a queue for messages from background threads
    message_queue = asyncio.Queue()
    
    # Add duplicate detection variables
    last_transcript = ""
    last_transcript_time = None
    
    async def send_queued_messages():
        """Background task to send queued messages"""
        while True:
            try:
                message = await message_queue.get()
                if message is None:  # Shutdown signal
                    break
                await websocket.send_text(json.dumps(message))
                message_queue.task_done()
            except Exception as e:
                logger.error(f"Error sending queued message: {e}")
                break
    
    # Start the message sender task
    sender_task = asyncio.create_task(send_queued_messages())
    
    def normalize_transcript(text):
        """Normalize transcript for comparison"""
        import re
        # Remove punctuation and convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
        return normalized
    
    def is_better_formatted(new_text, old_text):
        """Check if new text is better formatted than old text"""
        import re
        new_has_punct = bool(re.search(r'[.!?]', new_text))
        new_has_caps = new_text != new_text.lower()
        old_has_punct = bool(re.search(r'[.!?]', old_text))
        old_has_caps = old_text != old_text.lower()
        
        # Better if it has punctuation or capitalization that the old one doesn't
        return (new_has_punct and not old_has_punct) or (new_has_caps and not old_has_caps)
    
    def on_transcript_received(transcript: str, is_final: bool):
        """Callback for when transcript is received"""
        try:
            # Only send interim results for UI feedback
            if not is_final:
                message = {
                    "type": "interim_transcript",
                    "text": transcript,
                    "timestamp": datetime.now().isoformat()
                }
                # Put message in queue using the stored loop reference
                asyncio.run_coroutine_threadsafe(
                    message_queue.put(message), 
                    main_loop
                )
        except Exception as e:
            logger.error(f"Error queuing interim transcript: {e}")
    
    def on_turn_end(final_transcript: str):
        """Callback when turn ends - user stopped talking"""
        nonlocal last_transcript, last_transcript_time
        
        try:
            logger.info(f"Turn ended with final transcript: {final_transcript}")
            
            # Normalize for comparison
            normalized_new = normalize_transcript(final_transcript)
            normalized_last = normalize_transcript(last_transcript)
            
            current_time = datetime.now()
            
            # Check if this is a duplicate (same content within 2 seconds)
            if (normalized_new == normalized_last and 
                last_transcript_time and 
                (current_time - last_transcript_time).total_seconds() < 2):
                
                # Check if new version is better formatted
                if is_better_formatted(final_transcript, last_transcript):
                    logger.info(f"Updating with better formatted version: {final_transcript}")
                    
                    # Send update message to replace the previous one
                    message = {
                        "type": "turn_update",
                        "text": final_transcript,
                        "timestamp": current_time.isoformat(),
                        "message": "Updated with better formatting"
                    }
                    asyncio.run_coroutine_threadsafe(
                        message_queue.put(message), 
                        main_loop
                    )
                else:
                    logger.info(f"Skipped duplicate: {final_transcript}")
                    return
            else:
                # This is a new unique transcript
                logger.info(f"Sent to UI: {final_transcript}")
                
                # Send final transcript and turn end notification
                message = {
                    "type": "turn_end",
                    "text": final_transcript,
                    "timestamp": current_time.isoformat(),
                    "message": "User stopped talking"
                }
                asyncio.run_coroutine_threadsafe(
                    message_queue.put(message), 
                    main_loop
                )
            
            # Update last transcript tracking
            last_transcript = final_transcript
            last_transcript_time = current_time
            
        except Exception as e:
            logger.error(f"Error queuing turn end: {e}")
    
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
                            logger.info("Starting turn detection recording session")
                            transcriber = AssemblyAIStreamingTranscriber(sample_rate=16000)
                            if transcriber.start_streaming(on_transcript_received, on_turn_end):
                                await websocket.send_text(json.dumps({
                                    "type": "status",
                                    "message": "Turn detection started - speak and pause to see results!"
                                }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "message": "Failed to start turn detection service"
                                }))
                        
                        elif data.get("command") == "stop_recording":
                            logger.info("Stopping turn detection recording session")
                            if transcriber:
                                transcriber.stop_streaming()
                                transcriber = None
                            await websocket.send_text(json.dumps({
                                "type": "status",
                                "message": "Turn detection stopped"
                            }))
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                
                elif "bytes" in message:
                    # Handle audio data
                    audio_data = message["bytes"]
                    if transcriber and len(audio_data) > 0:
                        logger.debug(f"Streaming {len(audio_data)} bytes of audio for turn detection")
                        transcriber.stream_audio(audio_data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if transcriber:
            transcriber.stop_streaming()
        
        # Stop the sender task
        await message_queue.put(None)  # Shutdown signal
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass

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
