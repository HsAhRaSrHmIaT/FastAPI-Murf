"""Health check API endpoints"""
from fastapi import APIRouter, Request
from app.models.schemas import HealthStatus, ErrorTestResponse
from app.services.health_service import HealthService
from app.core.config import get_api_keys_from_request
# from app.core.logging import get_logger

# logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthStatus)
async def health_check(request: Request):
    """Check application health status"""
    # logger.info("Health check requested")
    
    # Extract API keys from request headers
    api_keys = get_api_keys_from_request(request=request)
    
    # Create health service instance with user API keys
    health_svc = HealthService()
    return health_svc.get_health_status(api_keys)
