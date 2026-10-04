from fastapi import APIRouter
from app.api.routes import health

api_router = APIRouter()

# Register sub-routes
api_router.include_router(health.router, prefix="", tags=["System"])
