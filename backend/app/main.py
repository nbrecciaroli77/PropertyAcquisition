import logging
import uuid
from collections.abc import Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths where Cache-Control: no-store must be enforced.
_NO_STORE_PREFIXES = ("/api/auth/", "/api/exports/", "/api/account/")

# Content-Security-Policy compatible with the React SPA + Google Fonts.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self';"
)


def create_app() -> FastAPI:
    from app.api.auth import router as auth_router
    from app.api.csv_intake import router as csv_intake_router
    from app.api.dev import router as dev_router
    from app.api.duplicates import router as duplicates_router
    from app.api.aliases import router as aliases_router
    from app.api.intake import router as intake_router
    from app.api.journeys import router as journeys_router
    from app.api.properties import router as properties_router
    from app.api.sources import router as sources_router
    from app.api.tasks import router as tasks_router
    from app.api.notifications import router as notifications_router
    from app.api.reports import router as reports_router
    from app.api.exports import router as exports_router
    from app.api.account import router as account_router
    from app.api.system import router as system_router
    from app.core.config import get_settings
    from app.db.base import dispose_engine

    settings = get_settings()
    app = FastAPI(title=settings.app_name, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def guard_and_correlate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        cid = request.headers.get("x-correlation-id") or uuid.uuid4().hex
        origin = request.headers.get("origin")
        if request.method in MUTATING_METHODS and origin and not settings.allows_origin(origin):
            logger.warning("rejected cross-origin write cid=%s origin=%s", cid, origin)
            return JSONResponse(
                {"detail": "Cross-origin request rejected"},
                status_code=403,
                headers={"x-correlation-id": cid},
            )
        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("unhandled error cid=%s path=%s", cid, request.url.path)
            return JSONResponse(
                {"detail": "An unexpected error occurred.", "reference": cid},
                status_code=500,
                headers={"x-correlation-id": cid},
            )

        # Security headers on every response.
        response.headers["x-correlation-id"] = cid
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["content-security-policy"] = _CSP

        # Sensitive routes must not be cached by any intermediary.
        path = request.url.path
        if any(path.startswith(p) for p in _NO_STORE_PREFIXES):
            response.headers["cache-control"] = "no-store, private"

        return response

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    app.include_router(system_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(journeys_router, prefix="/api")
    app.include_router(properties_router, prefix="/api")
    app.include_router(csv_intake_router, prefix="/api")   # must precede intake_router (avoids path collision)
    app.include_router(intake_router, prefix="/api")
    app.include_router(duplicates_router, prefix="/api")
    app.include_router(aliases_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(exports_router, prefix="/api")
    app.include_router(account_router, prefix="/api")
    app.include_router(dev_router, prefix="/api")
    return app
