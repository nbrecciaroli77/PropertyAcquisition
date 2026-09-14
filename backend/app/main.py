import logging
import uuid
from collections.abc import Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app() -> FastAPI:
    from app.api.auth import router as auth_router
    from app.api.dev import router as dev_router
    from app.api.intake import router as intake_router
    from app.api.journeys import router as journeys_router
    from app.api.properties import router as properties_router
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
            logging.warning("rejected cross-origin write cid=%s origin=%s", cid, origin)
            return JSONResponse(
                {"detail": "Cross-origin request rejected"},
                status_code=403,
                headers={"x-correlation-id": cid},
            )
        response: Response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    app.include_router(system_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(journeys_router, prefix="/api")
    app.include_router(properties_router, prefix="/api")
    app.include_router(intake_router, prefix="/api")
    app.include_router(dev_router, prefix="/api")
    return app
