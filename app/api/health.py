"""Health check API endpoints"""
from fastapi import APIRouter
from app.models.schemas import HealthStatus, ErrorTestResponse
from app.services.health_service import health_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthStatus)
async def health_check():
    """Check application health status"""
    logger.info("Health check requested")
    return health_service.get_health_status()


@router.get("/test-errors", response_model=ErrorTestResponse)
async def test_error_scenarios():
    """Test endpoint to simulate different error scenarios"""
    logger.info("Error scenario test requested")
    
    # Check service availability
    services = health_service.check_services()
    stt_working = services["stt_service"] == "available"
    
    # Generate status message
    if stt_working:
        fallback_message = "All systems operational - no fallback needed"
        overall_status = "healthy"
    else:
        fallback_message = "STT service unavailable - transcription not working"
        overall_status = "degraded"
    
    return ErrorTestResponse(
        stt_test="working" if stt_working else "missing_key",
        llm_test="working" if stt_working else "missing_key",
        tts_test="working" if stt_working else "missing_key",
        overall_status=overall_status,
        fallback_message=fallback_message
    )
