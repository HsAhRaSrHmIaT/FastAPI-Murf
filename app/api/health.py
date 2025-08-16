"""Health check API endpoints"""
from fastapi import APIRouter
from app.models.schemas import HealthStatus, ErrorTestResponse
from app.services.health_service import health_service
# from app.core.logging import get_logger

# logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthStatus)
async def health_check():
    """Check application health status"""
    # logger.info("Health check requested")
    return health_service.get_health_status()


@router.get("/test-errors", response_model=ErrorTestResponse)
async def test_error_scenarios():
    """Test endpoint to simulate different error scenarios"""
    # logger.info("Error scenario test requested")
    
    # Check service availability
    services = health_service.check_services()
    stt_working = services["stt_service"] == "available"
    llm_working = services["llm_service"] == "available"
    tts_working = services["tts_service"] == "available"
    
    # Generate fallback message based on service status
    fallback_message = None
    if not stt_working or not llm_working or not tts_working:
        fallback_message = health_service.generate_fallback_response(
            transcription_error="STT failed" if not stt_working else None,
            llm_error="LLM failed" if not llm_working else None,
            tts_error="TTS failed" if not tts_working else None
        )
    else:
        fallback_message = "All systems operational - no fallback needed"
    
    overall_status = "healthy" if (stt_working and llm_working and tts_working) else "degraded"
    
    return ErrorTestResponse(
        stt_test="working" if stt_working else "missing_key",
        llm_test="working" if llm_working else "missing_key",
        tts_test="working" if tts_working else "missing_key",
        overall_status=overall_status,
        fallback_message=fallback_message
    )
