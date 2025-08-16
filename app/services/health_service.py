"""Health monitoring service"""
from typing import List
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import HealthStatus
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.llm_service import llm_service
import time

logger = get_logger(__name__)


class HealthService:
    """Service for monitoring application health"""
    
    def __init__(self):
        logger.info("Health service initialized")
    
    def check_api_keys(self) -> List[str]:
        """
        Check for missing API keys
        
        Returns:
            List of missing API key names
        """
        missing_keys = []
        
        if not settings.google_api_key:
            missing_keys.append("GOOGLE_API_KEY")
        
        if not settings.murf_api_key:
            missing_keys.append("MURF_API_KEY")
            
        if not settings.murf_api_url:
            missing_keys.append("MURF_API_URL")
            
        if not settings.assemblyai_api_key:
            missing_keys.append("ASSEMBLYAI_API_KEY")
        
        return missing_keys
    
    def check_services(self) -> dict:
        """
        Check availability of all services
        
        Returns:
            Dictionary with service status
        """
        return {
            "stt_service": "available" if stt_service.is_available() else "unavailable",
            "llm_service": "available" if llm_service.is_available() else "unavailable", 
            "tts_service": "available" if tts_service.is_available() else "unavailable"
        }
    
    def get_health_status(self) -> HealthStatus:
        """
        Get overall health status
        
        Returns:
            HealthStatus object with current health information
        """
        missing_keys = self.check_api_keys()
        services = self.check_services()
        
        # Determine overall status
        if not missing_keys:
            status = "healthy"
        elif all(service == "unavailable" for service in services.values()):
            status = "down"
        else:
            status = "degraded"
        
        logger.info(f"Health check: {status}, missing keys: {missing_keys}")
        
        return HealthStatus(
            status=status,
            missing_api_keys=missing_keys,
            timestamp=time.time()
        )
    
    def generate_fallback_response(
        self, 
        transcription_error: str = None,
        llm_error: str = None, 
        tts_error: str = None
    ) -> str:
        """
        Generate appropriate fallback response based on which services failed
        
        Args:
            transcription_error: STT service error message
            llm_error: LLM service error message
            tts_error: TTS service error message
            
        Returns:
            Appropriate fallback message
        """
        if transcription_error and llm_error and tts_error:
            return "I'm experiencing technical difficulties with all services. Please try again later."
        elif transcription_error and llm_error:
            return "I'm having trouble understanding your audio and processing requests right now. Please try again later."
        elif transcription_error and tts_error:
            return "I'm having trouble with audio processing right now. Please try again later."
        elif llm_error and tts_error:
            return "I'm having trouble processing and responding to requests right now. Please try again later."
        elif transcription_error:
            return "I'm having trouble understanding the audio right now. Please try again or speak more clearly."
        elif llm_error:
            return "I'm having trouble processing your request right now. Please try again later."
        elif tts_error:
            return "I'm having trouble generating audio responses right now, but I can still process your requests."
        else:
            return "I'm having some technical difficulties right now. Please try again later."


# Global health service instance
health_service = HealthService()
