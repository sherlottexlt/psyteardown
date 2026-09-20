"""Stable, non-sensitive HTTP error mapping for the Product Studio API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from psyteardown.experience.models import DomainStateError
from psyteardown.product import ProductRepositoryError


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    issues: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id(request),
                "issues": issues or [],
            }
        },
    )
    response.headers["X-Request-ID"] = request_id(request)
    return response


def validation_issues(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project Pydantic errors without echoing rejected request values."""

    return [
        {
            "location": list(error.get("loc", ())),
            "code": str(error.get("type", "validation_error")),
            "message": str(error.get("msg", "Invalid value")),
        }
        for error in errors
    ]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            issues=validation_issues(exc.errors()),
        )

    @app.exception_handler(ValidationError)
    async def domain_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=422,
            code="domain_validation_error",
            message="The command violates the domain contract",
            issues=validation_issues(exc.errors()),
        )

    @app.exception_handler(ProductRepositoryError)
    async def repository_handler(
        request: Request, exc: ProductRepositoryError
    ) -> JSONResponse:
        message = str(exc)
        code = "revision_conflict" if "revision conflict" in message else "conflict"
        return error_response(
            request,
            status_code=409,
            code=code,
            message=message,
        )

    @app.exception_handler(DomainStateError)
    async def domain_state_handler(
        request: Request, exc: DomainStateError
    ) -> JSONResponse:
        message = str(exc)
        if message.startswith("unknown "):
            status_code = 404
            code = "not_found"
        elif "human-confirmed" in message or "requires" in message:
            status_code = 409
            code = "domain_gate"
        else:
            status_code = 409
            code = "invalid_state"
        return error_response(
            request,
            status_code=status_code,
            code=code,
            message=message,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected server error occurred",
        )
