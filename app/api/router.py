from fastapi import APIRouter
from app.api.routes import health, verifier, discovery

api_router = APIRouter()

# Register sub-routes
api_router.include_router(health.router, prefix="", tags=["System"])
api_router.include_router(verifier.router, prefix="", tags=["Deliverability"])
api_router.include_router(discovery.router, prefix="", tags=["Discovery"])
