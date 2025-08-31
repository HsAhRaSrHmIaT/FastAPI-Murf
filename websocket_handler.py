"""WebSocket handlers for real-time voice transcription"""
import json
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

# from app.core.logging import get_logger
from app.services.stt_service import AssemblyAIStreamingTranscriber
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService

# logger = get_logger(__name__)


class TurnDetectionWebSocketHandler:
    """WebSocket handler for turn detection voice transcription"""
    
    def __init__(self, websocket: WebSocket, api_keys: dict):
        self.websocket = websocket
        self.api_keys = api_keys
        print(f"[DEBUG] WebSocket handler initialized with API keys: {list(api_keys.keys())}")
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
        # logger.info("WebSocket connected for turn detection")

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
                # logger.error(f"Error sending queued message: {e}")
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
            # logger.error(f"Error queuing message: {e}")
            pass

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
            # logger.error(f"Error handling interim transcript: {e}")
            pass

    def _on_turn_end(self, final_transcript: str):
        """Callback when turn ends - user stopped talking"""
        try:
            # logger.info(f"Turn ended with final transcript: {final_transcript}")

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
                    # logger.info(f"Updating with better formatted version: {final_transcript}")
                    
                    # Send update message to replace the previous one
                    message = {
                        "type": "turn_update",
                        "text": final_transcript,
                        "timestamp": current_time.isoformat(),
                        "message": "Updated with better formatting"
                    }
                    self._queue_message(message)
                else:
                    # logger.info(f"Skipped duplicate: {final_transcript}")
                    return
            else:
                # This is a new unique transcript
                # logger.info(f"Sent to UI: {final_transcript}")

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
            # logger.error(f"Error handling turn end: {e}")
            pass

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
            # logger.error(f"Error starting LLM processing: {e}")
            pass

    async def _stream_llm_response(self, transcript: str):
        """Stream LLM response to the WebSocket"""
        try:
            from app.services.llm_service import LLMService
            from app.services.tts_service import TTSService
            # Send thinking status
            await self.message_queue.put({
                "type": "llm_thinking",
                "message": "AI is thinking...",
                "timestamp": datetime.now().isoformat()
            })
            llm = LLMService(api_key=self.api_keys['google_api_key'])
            murf_key = self.api_keys.get('murf_api_key')
            tts = TTSService(api_key=murf_key)
            print(f"[DEBUG] LLM available: {llm.is_available()}")
            print(f"[DEBUG] TTS available: {tts.is_available()}")
            print(f"[DEBUG] Murf API key: {murf_key if murf_key else 'NOT_SET'}")
            print(f"[DEBUG] TTS API key present: {bool(murf_key)}")
            if not llm.is_available():
                await self.message_queue.put({
                    "type": "llm_error",
                    "message": "AI service is not available",
                    "timestamp": datetime.now().isoformat()
                })
                return
            print(f"[LLM] Processing: {transcript}")
            await self.message_queue.put({
                "type": "llm_response_start",
                "message": "AI response starting...",
                "timestamp": datetime.now().isoformat()
            })
            accumulated_response = ""
            chunk_count = 0
            async for chunk in llm.generate_streaming_response(transcript, self.session_id):
                chunk_count += 1
                accumulated_response += chunk
                await self.message_queue.put({
                    "type": "llm_response_chunk",
                    "chunk": chunk,
                    "accumulated": accumulated_response,
                    "chunk_number": chunk_count,
                    "timestamp": datetime.now().isoformat()
                })
            await self.message_queue.put({
                "type": "llm_response_complete",
                "final_response": accumulated_response,
                "total_chunks": chunk_count,
                "timestamp": datetime.now().isoformat()
            })
            print(f"\n[LLM] Complete response ({chunk_count} chunks): {accumulated_response}")
            # TTS pipeline fix: check Murf API key before TTS
            if not murf_key or not tts.is_available():
                await self.message_queue.put({
                    "type": "tts_error",
                    "message": "TTS service is not available. Please check your Murf API key in settings.",
                    "timestamp": datetime.now().isoformat()
                })
                print("[DEBUG] TTS not available: Murf API key missing or invalid.")
                return
            try:
                print(f"[DEBUG] Starting TTS generation for text: {accumulated_response[:50]}...")
                print(f"[DEBUG] Using Murf API key: {tts.api_key[:10] if tts.api_key else 'None'}...")
                audio_b64 = await tts.generate_speech(accumulated_response)
                print(f"[DEBUG] TTS generation completed, audio length: {len(audio_b64) if audio_b64 else 0}")
                if audio_b64:
                    await self.message_queue.put({
                        "type": "tts_response",
                        "audio": audio_b64,
                        "timestamp": datetime.now().isoformat()
                    })
                    print("[DEBUG] TTS audio sent to client")
                else:
                    print("[DEBUG] TTS returned empty audio")
            except Exception as tts_exc:
                print(f"[DEBUG] TTS error: {tts_exc}")
                await self.message_queue.put({
                    "type": "tts_error",
                    "message": f"TTS service error: {tts_exc}",
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            # logger.error(f"Error streaming LLM response: {e}")
            await self.message_queue.put({
                "type": "llm_error",
                "message": f"Error generating AI response: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def handle_command(self, command: str):
        """Handle WebSocket commands"""
        if command == "start_recording":
            # logger.info("Starting turn detection recording session")
            self.transcriber = AssemblyAIStreamingTranscriber(
                sample_rate=16000, 
                api_key=self.api_keys.get('assemblyai_api_key')
            )
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
            # logger.info("Stopping turn detection recording session")
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
            # logger.debug(f"Streaming {len(audio_data)} bytes of audio for turn detection")
            self.transcriber.stream_audio(audio_data)
    
    async def disconnect(self):
        """Clean up resources on disconnect"""
        # logger.info("WebSocket disconnecting - cleaning up")
        
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
    
    # Initialize with empty API keys - client will send them via 'api_keys' message
    api_keys = {
        'assemblyai_api_key': None,
        'google_api_key': None,
        'murf_api_key': None
    }
    
    handler = TurnDetectionWebSocketHandler(websocket, api_keys)
    
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
                        
                        # Handle API keys message
                        if data.get("type") == "api_keys":
                            old_keys = handler.api_keys.copy()
                            handler.api_keys.update(data.get("data", {}))
                            print(f"[DEBUG] Updated API keys from client:")
                            print(f"[DEBUG]  Old: {old_keys}")
                            print(f"[DEBUG]  New: {handler.api_keys}")
                            continue
                        
                        command = data.get("command")
                        if command:
                            await handler.handle_command(command)
                    except json.JSONDecodeError:
                        # logger.error("Invalid JSON received")
                        pass

                elif "bytes" in message:
                    # Handle audio data
                    audio_data = message["bytes"]
                    handler.handle_audio_data(audio_data)

    except WebSocketDisconnect:
        # logger.info("WebSocket disconnected")
        pass
    except Exception as e:
        # logger.error(f"WebSocket error: {e}")
        pass
    finally:
        await handler.disconnect()
