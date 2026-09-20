"""FastAPI application factory for the local-first Product Studio API."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from psyteardown.api.errors import error_response, register_error_handlers
from psyteardown.api.projects import router as projects_router
from psyteardown.api.schemas import HealthResponse
from psyteardown.product import (
    ProductApplicationService,
    SQLiteProductRepository,
)


DEFAULT_PRODUCT_STORE = Path("output/product-studio/product.sqlite3")
DEFAULT_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "testserver"})
DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def create_app(
    *,
    database_path: Path | str | None = None,
    service: ProductApplicationService | None = None,
    clock: Callable[[], datetime] | None = None,
    id_factory: Callable[[str], str] | None = None,
    allowed_hosts: Sequence[str] = tuple(DEFAULT_ALLOWED_HOSTS),
    allowed_origins: Sequence[str] = DEFAULT_ALLOWED_ORIGINS,
) -> FastAPI:
    """Create an API app without opening persistence until lifespan starts."""

    owns_repository = service is None
    resolved_path = Path(
        database_path
        or os.getenv("PSYTEARDOWN_PRODUCT_STORE", str(DEFAULT_PRODUCT_STORE))
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository = None
        if service is not None:
            app.state.product_service = service
        else:
            repository = SQLiteProductRepository(resolved_path)
            kwargs = {}
            if clock is not None:
                kwargs["clock"] = clock
            if id_factory is not None:
                kwargs["id_factory"] = id_factory
            app.state.product_service = ProductApplicationService(
                repository, **kwargs
            )
        try:
            yield
        finally:
            app.state.product_service = None
            if owns_repository and repository is not None:
                repository.close()

    application = FastAPI(
        title="psyteardown Product Studio API",
        version="0.1.0",
        description=(
            "Local-first command and projection API for Product Studio. "
            "Model generation and other long-running work are not executed "
            "inside these synchronous endpoints."
        ),
        lifespan=lifespan,
    )
    register_error_handlers(application)

    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

    allowed_host_set = frozenset(allowed_hosts)

    @application.middleware("http")
    async def local_request_boundary(request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request.state.request_id = (
            supplied_request_id
            if _SAFE_REQUEST_ID.fullmatch(supplied_request_id)
            else uuid4().hex
        )
        host = request.url.hostname
        if allowed_host_set and host not in allowed_host_set:
            return error_response(
                request,
                status_code=400,
                code="host_not_allowed",
                message="Host is not allowed for this local Product Studio API",
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.get(
        "/api/v1/health", response_model=HealthResponse, tags=["system"]
    )
    async def health() -> HealthResponse:
        return HealthResponse()

    application.include_router(projects_router, prefix="/api/v1")
    return application


def run() -> None:
    """Run the localhost-only development API."""

    import uvicorn

    uvicorn.run(
        "psyteardown.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


app = create_app()
