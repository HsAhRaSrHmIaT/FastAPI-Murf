"""Speech-to-Text service using AssemblyAI"""
import assemblyai as aai
from app.core.config import settings
# from app.core.logging import get_logger
from app.models.schemas import TranscriptionResponse

# logger = get_logger(__name__)


class STTService:
    """Speech-to-Text service using AssemblyAI"""
    
    def __init__(self):
        if not settings.assemblyai_api_key:
            # logger.warning("AssemblyAI API key not found")
            self._transcriber = None
        else:
            aai.settings.api_key = settings.assemblyai_api_key
            self._transcriber = aai.Transcriber()
            # logger.info("STT service initialized with AssemblyAI")
    
    def is_available(self) -> bool:
        """Check if STT service is available"""
        return self._transcriber is not None
    
    async def transcribe_audio(self, audio_data: bytes) -> TranscriptionResponse:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Audio data as bytes
            
        Returns:
            TranscriptionResponse with transcribed text
            
        Raises:
            Exception: If transcription fails or service unavailable
        """
        if not self.is_available():
            raise Exception("AssemblyAI API key not configured")
        
        try:
            # logger.info(f"Starting transcription for {len(audio_data)} bytes of audio")
            
            transcript = self._transcriber.transcribe(audio_data)
            
            if transcript.status == aai.TranscriptStatus.error:
                # logger.error(f"Transcription failed: {transcript.error}")
                raise Exception(f"Transcription failed: {transcript.error}")
            
            if not transcript.text or transcript.text.strip() == "":
                # logger.warning("No speech detected in audio")
                raise Exception("No speech detected in the audio")

            # logger.info(f"Transcription successful: '{transcript.text[:50]}...'")

            return TranscriptionResponse(
                text=transcript.text,
                confidence=getattr(transcript, 'confidence', None),
                duration=getattr(transcript, 'duration', None)
            )
            
        except Exception as e:
            # logger.error(f"STT service error: {str(e)}")
            raise Exception(f"Speech-to-text failed: {str(e)}")


# Global STT service instance
stt_service = STTService()
