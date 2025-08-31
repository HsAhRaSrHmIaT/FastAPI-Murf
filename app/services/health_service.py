"""Health monitoring service"""
from typing import List
import time

from httpx import get
from app.core.config import settings, get_api_key_from_env
# from app.core.logging import get_logger
from app.models.schemas import HealthStatus

from app.services.stt_service import STTService
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService

# logger = get_logger(__name__)


class HealthService:
    """Service for monitoring application health"""
    
    def __init__(self):
        # logger.info("Health service initialized")
        pass
    
    def check_api_keys(self) -> List[str]:
        """
        Check for missing API keys
        
        Note: API keys are now handled per-user via headers, so this mainly
        checks if any keys are provided in the current request.
        
        Returns:
            List of missing API key names (empty if all keys are provided)
        """
        # Since we now use per-user API keys, we don't check environment variables
        # The actual key validation happens in check_services()
        return []
    
    def check_services(self, api_keys: dict = None) -> dict:
        """
        Check availability of all services
        
        Args:
            api_keys: Dictionary of API keys from request headers (optional)
            
        Returns:
            Dictionary with service status
        """
        from app.services.stt_service import STTService
        from app.services.llm_service import LLMService  
        from app.services.tts_service import TTSService
        
        # Use provided API keys or None
        assemblyai_key = api_keys.get('assemblyai_api_key') if api_keys else None
        google_key = api_keys.get('google_api_key') if api_keys else None
        murf_key = api_keys.get('murf_api_key') if api_keys else None
        
        # Create service instances with provided API keys (or None)
        stt = STTService(api_key=assemblyai_key)
        llm = LLMService(api_key=google_key)
        tts = TTSService(api_key=murf_key)
        
        return {
            "stt_service": "available" if stt.is_available() else "unavailable",
            "llm_service": "available" if llm.is_available() else "unavailable", 
            "tts_service": "available" if tts.is_available() else "unavailable"
        }
    
    def get_health_status(self, api_keys: dict = None) -> HealthStatus:
        """
        Get overall health status
        
        Args:
            api_keys: Dictionary of API keys from request headers (optional)
            
        Returns:
            HealthStatus object with current health information
        """
        missing_keys = self.check_api_keys()
        services = self.check_services(api_keys)
        
        # Count available services
        available_services = sum(1 for status in services.values() if status == "available")
        total_services = len(services)
        
        # Determine overall status
        # In the per-user API key system:
        # - If no API keys provided: "Down" (user needs to provide keys)
        # - If API keys provided: "Healthy" if all services available, "Degraded" if some available
        if api_keys and any(api_keys.values()):  # Check if any API keys are provided
            if available_services > 0:
                status = "Healthy" if available_services == total_services else "Degraded"
            else:
                status = "Down"
        else:
            # No API keys provided - system is down until user provides keys
            status = "Down"

        # logger.info(f"Health check: {status}, services: {services}")
        
        return HealthStatus(
            status=status,
            missing_api_keys=[],  # No longer relevant in per-user system
            timestamp=time.time()
        )


# Global health service instance
health_service = HealthService()
