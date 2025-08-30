"""Health monitoring service"""
from typing import List

from httpx import get
from app.core.config import settings, get_api_key
# from app.core.logging import get_logger
from app.models.schemas import HealthStatus

from app.services.stt_service import stt_service
from app.services.llm_service import llm_service
import time
from app.services.tts_service import tts_service

# logger = get_logger(__name__)


class HealthService:
    """Service for monitoring application health"""
    
    def __init__(self):
        # logger.info("Health service initialized")
        pass
    
    def check_api_keys(self) -> List[str]:
        """
        Check for missing API keys
        
        Returns:
            List of missing API key names
        """
        missing_keys = []

        if not get_api_key("assemblyai_api_key"):
            missing_keys.append("ASSEMBLYAI_API_KEY")
            
        if not get_api_key("google_api_key"):
            missing_keys.append("GOOGLE_API_KEY")

        if not get_api_key("murf_api_key"):
            missing_keys.append("MURF_API_KEY")
        
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
        
        # Count available services
        available_services = sum(1 for status in services.values() if status == "available")
        total_services = len(services)
        
        # Determine overall status
        if not missing_keys and available_services == total_services:
            status = "Healthy"
        elif available_services == 0:
            status = "Down"
        else:
            status = "Degraded"

        # logger.info(f"Health check: {status}, missing keys: {missing_keys}, services: {services}")
        
        return HealthStatus(
            status=status,
            missing_api_keys=missing_keys,
            timestamp=time.time()
        )


# Global health service instance
health_service = HealthService()
