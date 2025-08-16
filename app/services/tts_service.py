"""Text-to-Speech service using Murf AI"""
import requests
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import SpeechRequest, SpeechResponse

logger = get_logger(__name__)


class TTSService:
    """Text-to-Speech service using Murf AI"""
    
    def __init__(self):
        self.api_key = settings.murf_api_key
        self.api_url = settings.murf_api_url
        
        if not self.api_key or not self.api_url:
            logger.warning("Murf AI API credentials not found")
        else:
            logger.info("TTS service initialized with Murf AI")
    
    def is_available(self) -> bool:
        """Check if TTS service is available"""
        return bool(self.api_key and self.api_url)
    
    async def generate_speech(self, request: SpeechRequest) -> SpeechResponse:
        """
        Generate speech from text
        
        Args:
            request: SpeechRequest with text and voice settings
            
        Returns:
            SpeechResponse with audio URL
            
        Raises:
            Exception: If speech generation fails or service unavailable
        """
        if not self.is_available():
            raise Exception("Murf AI API credentials not configured")
        
        try:
            logger.info(f"Generating speech for text: '{request.text[:50]}...'")
            
            payload = {
                "text": request.text,
                "voice_id": request.voice_id.value,
                "language": request.language.value
            }
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload,
                timeout=30  # 30 second timeout
            )
            
            if response.status_code != 200:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                raise Exception(f"TTS API returned status {response.status_code}: {response.text}")
            
            result = response.json()
            audio_url = result.get("audioFile")
            
            if not audio_url:
                logger.error("No audio URL received from TTS service")
                raise Exception("No audio URL received from TTS service")
            
            logger.info(f"Speech generation successful: {audio_url}")
            
            return SpeechResponse(audio_url=audio_url)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TTS network error: {str(e)}")
            raise Exception(f"Text-to-speech network error: {str(e)}")
        except Exception as e:
            logger.error(f"TTS service error: {str(e)}")
            raise Exception(f"Text-to-speech failed: {str(e)}")


# Global TTS service instance
tts_service = TTSService()
