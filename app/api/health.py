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
