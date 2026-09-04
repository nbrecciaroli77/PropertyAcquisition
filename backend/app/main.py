import logging
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    from app.api.system import router as system_router
    from app.core.config import get_settings

    settings = get_settings()
    app = FastAPI(title=settings.app_name, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_id(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        cid = request.headers.get("x-correlation-id") or uuid.uuid4().hex
        response: Response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response

    app.include_router(system_router, prefix="/api")
    return app
