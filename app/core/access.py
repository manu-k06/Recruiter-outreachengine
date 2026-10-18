"""A single-owner gate for the hosted workspace, not a multi-user account system."""
import base64
import binascii
import secrets

from fastapi.responses import JSONResponse


def install_workspace_access(app, config):
    password = config.WORKSPACE_PASSWORD.get_secret_value() if config.WORKSPACE_PASSWORD else ""
    configured = bool(password and config.WORKSPACE_USERNAME)

    @app.middleware("http")
    async def protect_workspace(request, call_next):
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        if config.VERCEL and (not configured or len(password) < 16 or not config.DATABASE_URL):
            return JSONResponse(status_code=503, content={"detail": "Hosted workspace setup is incomplete."})
        if configured:
            valid = False
            try:
                scheme, token = request.headers.get("authorization", "").split(" ", 1)
                decoded = base64.b64decode(token, validate=True).decode("utf-8")
                username, supplied = decoded.split(":", 1)
                valid = (scheme.lower() == "basic"
                         and secrets.compare_digest(username.encode(), config.WORKSPACE_USERNAME.encode())
                         and secrets.compare_digest(supplied.encode(), password.encode()))
            except (ValueError, UnicodeError, binascii.Error):
                pass
            if not valid:
                return JSONResponse(status_code=401, content={"detail": "Sign in to your workspace."},
                                    headers={"WWW-Authenticate": 'Basic realm="Outreach workspace", charset="UTF-8"', "Cache-Control": "no-store"})
            # Browsers can attach Basic credentials automatically. Reject cross-site writes.
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                expected = f"{request.url.scheme}://{request.url.netloc}"
                if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected):
                    return JSONResponse(status_code=403, content={"detail": "Cross-site writes are not allowed."})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response
