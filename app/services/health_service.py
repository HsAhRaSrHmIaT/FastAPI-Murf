"""Health monitoring service"""
from typing import List
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import HealthStatus
from app.services.stt_service import stt_service
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
            
        if not settings.assemblyai_api_key:
            missing_keys.append("ASSEMBLYAI_API_KEY")
            
        if not settings.google_api_key:
            missing_keys.append("GOOGLE_API_KEY")
        
        return missing_keys
    
    def check_services(self) -> dict:
        """
        Check availability of all services
        
        Returns:
            Dictionary with service status
        """
        return {
            "stt_service": "available" if stt_service.is_available() else "unavailable",
            "llm_service": "available" if llm_service.is_available() else "unavailable"
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
        all_services_available = (
            services["stt_service"] == "available" and 
            services["llm_service"] == "available"
        )
        
        if not missing_keys and all_services_available:
            status = "healthy"
        elif not all_services_available:
            status = "down"
        else:
            status = "degraded"
        
        logger.info(f"Health check: {status}, missing keys: {missing_keys}, services: {services}")
        
        return HealthStatus(
            status=status,
            missing_api_keys=missing_keys,
            timestamp=time.time()
        )


# Global health service instance
health_service = HealthService()
