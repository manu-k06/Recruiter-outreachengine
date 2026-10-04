from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router

def create_application() -> FastAPI:
    """
    Application Factory Pattern.
    Creating the app via a factory allows easy testing and configuration injection.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        description="High-performance backend engine for automated recruiter discovery and verified cold outreach."
    )

    # CORS (Cross-Origin Resource Sharing) Setup
    # Allows the frontend (e.g. Vite on localhost:5173) to communicate with this backend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Open in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API Router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health"
        }

    return app

app = create_application()
