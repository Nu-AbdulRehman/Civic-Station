"""The single error seam: every error leaves the API in the 00-conventions §4 shape."""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.domain.errors import (
    ComplaintNotFoundError,
    InvalidTransitionError,
    RateLimitExceededError,
)
from app.observability.logging import get_logger

log = get_logger(__name__)

_HTTP_CODES = {
    400: ("validation_error", "Request validation failed."),
    404: ("not_found", "Resource not found."),
    405: ("method_not_allowed", "Method not allowed."),
    413: ("payload_too_large", "Request body exceeds 64 KiB."),
    415: ("unsupported_media_type", "Content-Type must be application/json."),
}


def error_response(
    status: int,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    body = {"error": error, "request_id": request_id, **(extra or {})}
    return JSONResponse(body, status_code=status, headers=headers)


def _field_name(loc: tuple[int | str, ...]) -> str:
    """('body', 'text') -> 'text'; ('path', 'id') -> 'id'; ('body',) -> 'body'."""
    named = [str(p) for p in loc[1:] if isinstance(p, str)]
    return ".".join(named) or str(loc[0])


async def _validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only type and msg: pydantic's `input` could echo reporter_contact back (FR-BE-023).
    fields = [
        {"field": _field_name(tuple(e["loc"])), "rule": e["type"], "detail": e["msg"]}
        for e in exc.errors()
    ]
    return error_response(400, "validation_error", "Request validation failed.", fields)


async def _http(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code, message = _HTTP_CODES.get(exc.status_code, ("http_error", "Request failed."))
    return error_response(exc.status_code, code, message, headers=dict(exc.headers or {}))


async def _not_found(_: Request, exc: Exception) -> JSONResponse:
    return error_response(404, "not_found", str(exc))


async def _invalid_transition(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, InvalidTransitionError)
    log.info("status.transition_rejected", current=exc.current, target=exc.target)
    return error_response(409, "invalid_transition", str(exc))


async def _rate_limited(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceededError)
    return error_response(
        429,
        "rate_limited",
        str(exc),
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(HTTPException, _http)
    app.add_exception_handler(ComplaintNotFoundError, _not_found)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition)
    app.add_exception_handler(RateLimitExceededError, _rate_limited)
