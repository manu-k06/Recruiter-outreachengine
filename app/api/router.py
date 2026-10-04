from fastapi import APIRouter
from app.api.routes import health, verifier, discovery, pitch, outbox, resume, ai_studio

api_router = APIRouter()

# Register all modular sub-routes
api_router.include_router(health.router, prefix="", tags=["System"])
api_router.include_router(verifier.router, prefix="", tags=["Deliverability"])
api_router.include_router(discovery.router, prefix="", tags=["Discovery"])
api_router.include_router(pitch.router, prefix="", tags=["Pitch Generation"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume & Profile"])
api_router.include_router(ai_studio.router, prefix="/ai", tags=["AI Studio & Reviewer"])
api_router.include_router(outbox.router, prefix="/outbox", tags=["Outbox & Safeguards"])
