from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def check_health():
    """
    Health check endpoint returning service readiness.
    Used by load balancers, orchestrators, and frontend status checks.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "online",
            "verifier_engine": "ready",
            "discovery_engine": "ready"
        }
    )
