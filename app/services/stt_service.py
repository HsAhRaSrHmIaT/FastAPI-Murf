"""Speech-to-Text service using AssemblyAI"""
import assemblyai as aai
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import TranscriptionResponse
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions, StreamingParameters, 
    StreamingEvents
)
from typing import Optional, Callable

logger = get_logger(__name__)

class AssemblyAIStreamingTranscriber:
    """AssemblyAI streaming transcriber for real-time audio"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.client = None
        self.on_transcript_callback: Optional[Callable] = None
        self.on_turn_end_callback: Optional[Callable] = None
        self.current_turn_transcript = ""

        if not settings.assemblyai_api_key:
            logger.warning("AssemblyAI API key not found")
            return
            
        aai.settings.api_key = settings.assemblyai_api_key
        logger.info(f"Initializing AssemblyAI streaming with sample rate: {sample_rate}")
        
    def start_streaming(self, on_transcript: Callable = None, on_turn_end: Callable = None):
        """Start streaming transcription session"""
        if not settings.assemblyai_api_key:
            logger.error("Cannot start streaming: AssemblyAI API key not configured")
            return False
            
        try:
            self.on_transcript_callback = on_transcript
            self.on_turn_end_callback = on_turn_end
            self.current_turn_transcript = ""
            
            self.client = StreamingClient(
                StreamingClientOptions(
                    api_key=settings.assemblyai_api_key,
                    api_host="streaming.assemblyai.com"
                )
            )
            
            # Set up event handlers with correct signatures
            self.client.on(StreamingEvents.Begin, self._on_begin)
            self.client.on(StreamingEvents.Turn, self._on_turn)
            self.client.on(StreamingEvents.Termination, self._on_termination)
            self.client.on(StreamingEvents.Error, self._on_error)
            
            # Connect with streaming parameters
            self.client.connect(StreamingParameters(
                sample_rate=self.sample_rate,
                format_turns=True,
                interim_results=True,
                end_of_turn_silence_threshold=500,
                voice_activity_threshold=0.5
            ))
            
            logger.info("AssemblyAI streaming session started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False
    
    def stream_audio(self, audio_chunk: bytes):
        """Stream audio chunk to AssemblyAI"""
        if self.client:
            try:
                self.client.stream(audio_chunk)
            except Exception as e:
                logger.error(f"Error streaming audio: {e}")
    
    def stop_streaming(self):
        """Stop streaming session"""
        if self.client:
            try:
                self.client.disconnect(terminate=True)
                self.client = None
                logger.info("AssemblyAI streaming session stopped")
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
    
    def _on_begin(self, client, event):
        """Handle streaming session begin event"""
        try:
            session_id = getattr(event, 'id', 'unknown')
            logger.info(f"Streaming session started: {session_id}")
            print(f"[AssemblyAI] Session Started: {session_id}")
        except Exception as e:
            logger.error(f"Error in _on_begin: {e}")
            print("[AssemblyAI] Session Started")
    
    def _on_turn(self, client, event):
        """Handle turn event with transcript"""
        try:
            transcript = getattr(event, 'transcript', '').strip()
            is_end_of_turn = getattr(event, 'end_of_turn', False)

            if transcript:
                self.current_turn_transcript = transcript

                logger.info(f"Turn Transcript: {transcript} (end_of_turn: {is_end_of_turn})")
                print(f"[TURN] {transcript}")
                print(f"   - End of Turn: {is_end_of_turn}")

                if is_end_of_turn:
                    print(f"[TURN COMPLETE] Final: {transcript}")
                    print("   - User stopped talking")

                    # ONLY send to UI when turn actually ends (user paused)
                    if self.on_turn_end_callback:
                        try:
                            self.on_turn_end_callback(transcript)
                        except Exception as e:
                            logger.error(f"Error in turn end callback: {e}")

                    self.current_turn_transcript = ""
                else:
                    # Interim result during speaking - only send for real-time feedback
                    print("   - Still speaking (interim)")
                    
                    # Send interim results for status display only
                    if self.on_transcript_callback:
                        try:
                            self.on_transcript_callback(transcript, False, False)
                        except Exception as e:
                            logger.error(f"Error in transcript callback: {e}")

            else:
                if self.on_transcript_callback:
                    try:
                        self.on_transcript_callback(transcript, False, False)
                    except Exception as e:
                        logger.error(f"Error in transcript callback: {e}")

        except Exception as e:
            logger.error(f"Error in _on_turn: {e}")
    
    def _on_termination(self, client, event):
        """Handle session termination"""
        try:
            duration = getattr(event, 'audio_duration_seconds', 'unknown')
            logger.info(f"Session terminated after {duration} seconds")
            print(f"[AssemblyAI] Session terminated - Duration: {duration}s")
        except Exception as e:
            logger.error(f"Error in _on_termination: {e}")
            print("[AssemblyAI] Session terminated")
    
    def _on_error(self, client, error):
        """Handle streaming errors"""
        try:
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Streaming error: {error_msg}")
            print(f"[ERROR] Streaming error: {error_msg}")
        except Exception as e:
            logger.error(f"Error in _on_error: {e}")
            print("[ERROR] Unknown streaming error")

class STTService:
    """Speech-to-Text service using AssemblyAI"""
    
    def __init__(self):
        if not settings.assemblyai_api_key:
            logger.warning("AssemblyAI API key not found")
            self._transcriber = None
        else:
            aai.settings.api_key = settings.assemblyai_api_key
            self._transcriber = aai.Transcriber()
            logger.info("STT service initialized with AssemblyAI")
    
    def is_available(self) -> bool:
        """Check if STT service is available"""
        return self._transcriber is not None
    
    async def transcribe_audio(self, audio_data: bytes) -> TranscriptionResponse:
        """Transcribe audio data to text (for non-streaming use)"""
        if not self.is_available():
            raise Exception("AssemblyAI API key not configured")
        
        try:
            logger.info(f"Starting transcription for {len(audio_data)} bytes of audio")
            
            transcript = self._transcriber.transcribe(audio_data)
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Transcription failed: {transcript.error}")
                raise Exception(f"Transcription failed: {transcript.error}")
            
            if not transcript.text or transcript.text.strip() == "":
                logger.warning("No speech detected in audio")
                raise Exception("No speech detected in the audio")
            
            logger.info(f"Transcription successful: '{transcript.text[:50]}...'")
            
            return TranscriptionResponse(
                text=transcript.text,
                confidence=getattr(transcript, 'confidence', None),
                duration=getattr(transcript, 'duration', None)
            )
            
        except Exception as e:
            logger.error(f"STT service error: {str(e)}")
            raise Exception(f"Speech-to-text failed: {str(e)}")

# Global instances
stt_service = STTService()
