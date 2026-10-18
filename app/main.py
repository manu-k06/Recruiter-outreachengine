from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.access import install_workspace_access
from app.api.router import api_router
from app.core.storage import SQLiteStore, StorageUnavailableError

def create_application(database_path: str | Path | None = None, config=None) -> FastAPI:
    """
    Application Factory Pattern.
    Creating the app via a factory allows easy testing and configuration injection.
    """
    config = config or settings
    if database_path is None and config.DATABASE_URL:
        from app.core.postgres import PostgresStore
        store = PostgresStore(config.DATABASE_URL.get_secret_value(), config.DAILY_SEND_LIMIT)
    else:
        store = SQLiteStore(database_path if database_path is not None else config.DATABASE_PATH, config.DAILY_SEND_LIMIT)

    @asynccontextmanager
    async def lifespan(app):
        # Fail startup if durable writes cannot be provided; never silently use memory.
        if not config.VERCEL or config.DATABASE_URL:
            await run_in_threadpool(store.initialize)
        yield

    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        description="High-performance backend engine for automated recruiter discovery and verified cold outreach."
    )
    app.state.store = store

    @app.exception_handler(StorageUnavailableError)
    async def storage_error(request: Request, exc: StorageUnavailableError):
        logging.getLogger(__name__).error("Persistent storage operation failed", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "Persistent storage is unavailable. The operation was not completed."})

    # Dashboard and API share one origin; no cross-site browser access is needed.
    install_workspace_access(app, config)

    @app.get("/api/v1/workspace", tags=["Workspace"])
    def workspace():
        return store.workspace_summary()

    # Mount API Router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    web_path = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    app.mount("/assets", StaticFiles(directory=web_path / "assets", check_dir=False), name="assets")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(web_path / "index.html")

    @app.get("/")
    async def root(request: Request):
        if "text/html" in request.headers.get("accept", ""):
            return RedirectResponse("/dashboard")
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "docs": "/docs",
            "dashboard": "/dashboard",
            "health": f"{settings.API_V1_STR}/health"
        }

    return app

app = create_application()
