"""WebSocket handlers for real-time voice transcription"""
import json
import asyncio
from datetime import datetime
from typing import Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.stt_service import AssemblyAIStreamingTranscriber
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service

logger = get_logger(__name__)


class TurnDetectionWebSocketHandler:
    """WebSocket handler for turn detection voice transcription"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.transcriber: Optional[AssemblyAIStreamingTranscriber] = None
        self.main_loop = None
        self.message_queue = None
        self.sender_task = None
        self.last_transcript = ""
        self.last_transcript_time = None
        self.session_id = f"ws_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # Unique session ID
    
    async def connect(self):
        """Accept WebSocket connection and initialize"""
        await self.websocket.accept()
        logger.info("WebSocket connected for turn detection")
        
        # Get the current event loop for thread-safe access
        self.main_loop = asyncio.get_running_loop()
        
        # Create a queue for messages from background threads
        self.message_queue = asyncio.Queue()
        
        # Start the message sender task
        self.sender_task = asyncio.create_task(self._send_queued_messages())
        
        # Send connection confirmation to client
        await self._send_message({
            "type": "connection",
            "message": "Connected to turn detection voice streaming server"
        })
    
    async def _send_queued_messages(self):
        """Background task to send queued messages"""
        while True:
            try:
                message = await self.message_queue.get()
                if message is None:  # Shutdown signal
                    break
                await self.websocket.send_text(json.dumps(message))
                self.message_queue.task_done()
            except Exception as e:
                logger.error(f"Error sending queued message: {e}")
                break
    
    async def _send_message(self, message: dict):
        """Send message directly to WebSocket"""
        await self.websocket.send_text(json.dumps(message))
    
    def _queue_message(self, message: dict):
        """Queue message to be sent from background thread"""
        try:
            asyncio.run_coroutine_threadsafe(
                self.message_queue.put(message), 
                self.main_loop
            )
        except Exception as e:
            logger.error(f"Error queuing message: {e}")
    
    @staticmethod
    def _normalize_transcript(text: str) -> str:
        """Normalize transcript for comparison"""
        import re
        # Remove punctuation and convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
        return normalized
    
    @staticmethod
    def _is_better_formatted(new_text: str, old_text: str) -> bool:
        """Check if new text is better formatted than old text"""
        import re
        new_has_punct = bool(re.search(r'[.!?]', new_text))
        new_has_caps = new_text != new_text.lower()
        old_has_punct = bool(re.search(r'[.!?]', old_text))
        old_has_caps = old_text != old_text.lower()
        
        # Better if it has punctuation or capitalization that the old one doesn't
        return (new_has_punct and not old_has_punct) or (new_has_caps and not old_has_caps)
    
    def _on_transcript_received(self, transcript: str, is_final: bool):
        """Callback for when transcript is received"""
        try:
            # Only send interim results for UI feedback
            if not is_final:
                message = {
                    "type": "interim_transcript",
                    "text": transcript,
                    "timestamp": datetime.now().isoformat()
                }
                self._queue_message(message)
        except Exception as e:
            logger.error(f"Error handling interim transcript: {e}")
    
    def _on_turn_end(self, final_transcript: str):
        """Callback when turn ends - user stopped talking"""
        try:
            logger.info(f"Turn ended with final transcript: {final_transcript}")
            
            # Normalize for comparison
            normalized_new = self._normalize_transcript(final_transcript)
            normalized_last = self._normalize_transcript(self.last_transcript)
            
            current_time = datetime.now()
            
            # Check if this is a duplicate (same content within 2 seconds)
            if (normalized_new == normalized_last and 
                self.last_transcript_time and 
                (current_time - self.last_transcript_time).total_seconds() < 2):
                
                # Check if new version is better formatted
                if self._is_better_formatted(final_transcript, self.last_transcript):
                    logger.info(f"Updating with better formatted version: {final_transcript}")
                    
                    # Send update message to replace the previous one
                    message = {
                        "type": "turn_update",
                        "text": final_transcript,
                        "timestamp": current_time.isoformat(),
                        "message": "Updated with better formatting"
                    }
                    self._queue_message(message)
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
                self._queue_message(message)
                
                # Now send the transcript to LLM for streaming response
                # Check for search triggers before sending to LLM
                lowered = final_transcript.lower().strip()
                # Simple triggers: start with 'search for' or 'find' or 'search'
                if lowered.startswith("search for ") or lowered.startswith("find ") or lowered.startswith("search "):
                    # Extract the query phrase after the trigger word
                    query = final_transcript.split(None, 2)[-1] if len(final_transcript.split()) > 1 else ""
                    # Send a prompt to the UI to confirm (yellow message) with actions
                    message = {
                        "type": "search_prompt",
                        "query": query,
                        "message": f"Search results for: \"{query}\"\nOpen search page to view results in a new tab.",
                        "timestamp": current_time.isoformat()
                    }
                    self._queue_message(message)
                else:
                    self._process_transcript_with_llm(final_transcript)
            
            # Update last transcript tracking
            self.last_transcript = final_transcript
            self.last_transcript_time = current_time
            
        except Exception as e:
            logger.error(f"Error handling turn end: {e}")
    
    def _process_transcript_with_llm(self, transcript: str):
        """Process transcript with LLM and stream response"""
        try:
            # Queue the LLM processing as an async task
            if self.main_loop:
                asyncio.run_coroutine_threadsafe(
                    self._stream_llm_response(transcript),
                    self.main_loop
                )
        except Exception as e:
            logger.error(f"Error starting LLM processing: {e}")
    
    async def _stream_llm_response(self, transcript: str):
        """Stream LLM response to the WebSocket"""
        try:
            # Send thinking status
            await self.message_queue.put({
                "type": "llm_thinking",
                "message": "AI is thinking...",
                "timestamp": datetime.now().isoformat()
            })
            
            if not llm_service.is_available():
                await self.message_queue.put({
                    "type": "llm_error",
                    "message": "AI service is not available",
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            logger.info(f"Sending transcript to LLM: '{transcript[:50]}...'")
            print(f"[LLM] Processing: {transcript}")
            
            # Send start of streaming response
            await self.message_queue.put({
                "type": "llm_response_start",
                "message": "AI response starting...",
                "timestamp": datetime.now().isoformat()
            })
            
            accumulated_response = ""
            chunk_count = 0
            
            # Stream response from LLM
            async for chunk in llm_service.generate_streaming_response(transcript, self.session_id):
                chunk_count += 1
                accumulated_response += chunk
                
                # Send each chunk to the WebSocket
                await self.message_queue.put({
                    "type": "llm_response_chunk",
                    "chunk": chunk,
                    "accumulated": accumulated_response,
                    "chunk_number": chunk_count,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Print to console as requested
                print(f"[LLM Chunk {chunk_count}] {chunk}", end="", flush=True)
            
            # Send completion notification
            await self.message_queue.put({
                "type": "llm_response_complete",
                "final_response": accumulated_response,
                "total_chunks": chunk_count,
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"\n[LLM] Complete response ({chunk_count} chunks): {accumulated_response}")
            logger.info(f"LLM streaming complete. Total chunks: {chunk_count}, Final length: {len(accumulated_response)}")

            # Send accumulated LLM response to TTS service and print base64 audio
            try:
                audio_b64 = await tts_service(accumulated_response)
                # The tts_service function already prints the base64 audio to the console
                logger.info(f"Generated audio for LLM response (base64): {audio_b64[:100]}... (length: {len(audio_b64)})")
                if audio_b64:
                    await self.message_queue.put({
                        "type": "tts_response",
                        "audio": audio_b64,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as tts_exc:
                logger.error(f"Error sending LLM response to TTS service: {tts_exc}")

        except Exception as e:
            logger.error(f"Error streaming LLM response: {e}")
            await self.message_queue.put({
                "type": "llm_error",
                "message": f"Error generating AI response: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def handle_command(self, command: str):
        """Handle WebSocket commands"""
        if command == "start_recording":
            logger.info("Starting turn detection recording session")
            self.transcriber = AssemblyAIStreamingTranscriber(sample_rate=16000)
            if self.transcriber.start_streaming(self._on_transcript_received, self._on_turn_end):
                await self._send_message({
                    "type": "status",
                    "message": "Turn detection started - speak and pause to see results!"
                })
            else:
                await self._send_message({
                    "type": "error",
                    "message": "Failed to start turn detection service"
                })
        
        elif command == "stop_recording":
            logger.info("Stopping turn detection recording session")
            if self.transcriber:
                self.transcriber.stop_streaming()
                self.transcriber = None
            await self._send_message({
                "type": "status",
                "message": "Turn detection stopped"
            })
    
    def handle_audio_data(self, audio_data: bytes):
        """Handle incoming audio data"""
        if self.transcriber and len(audio_data) > 0:
            logger.debug(f"Streaming {len(audio_data)} bytes of audio for turn detection")
            self.transcriber.stream_audio(audio_data)
    
    async def disconnect(self):
        """Clean up resources on disconnect"""
        logger.info("WebSocket disconnecting - cleaning up")
        
        # Stop transcriber
        if self.transcriber:
            self.transcriber.stop_streaming()
            self.transcriber = None
        
        # Stop the sender task
        if self.message_queue:
            await self.message_queue.put(None)  # Shutdown signal
        
        if self.sender_task:
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for turn detection"""
    handler = TurnDetectionWebSocketHandler(websocket)
    
    try:
        await handler.connect()
        
        while True:
            # Receive message from client
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    # Handle text commands
                    try:
                        data = json.loads(message["text"])
                        command = data.get("command")
                        if command:
                            await handler.handle_command(command)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                
                elif "bytes" in message:
                    # Handle audio data
                    audio_data = message["bytes"]
                    handler.handle_audio_data(audio_data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await handler.disconnect()
