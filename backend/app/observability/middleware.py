"""Request middleware: request id, body guards, request logging, HTTP metrics (03-M2 §2.3).

One pure-ASGI middleware so the order inside it is explicit. CORS wraps it from outside.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import error_response
from app.observability.logging import get_logger
from app.observability.metrics import HTTP_DURATION, HTTP_REQUESTS

MAX_BODY_BYTES = 64 * 1024
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_WRITE_METHODS = {"POST", "PUT", "PATCH"}
_UNMATCHED = "<unmatched>"

log = get_logger(__name__)


class _BodyTooLargeError(HTTPException):
    """An HTTPException, so FastAPI's body parser re-raises it instead of turning it into a 400."""

    def __init__(self) -> None:
        super().__init__(413)


def resolve_request_id(inbound: str | None) -> str:
    """Accept the caller's id only if it cannot inject a header or a log line (FR-BE-024)."""
    if inbound is not None and _REQUEST_ID_RE.fullmatch(inbound):
        return inbound
    return str(uuid.uuid4())


class RequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = resolve_request_id(headers.get("x-request-id"))
        method: str = scope["method"]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False
        log.info("request.started", method=method, path=scope["path"])

        async def send_with_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", request_id.encode()))
            await send(message)

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise _BodyTooLargeError
            return message

        try:
            rejection = _reject_body(method, scope["path"], headers)
            if rejection is not None:
                await rejection(scope, receive, send_with_id)
            else:
                await self.app(scope, limited_receive, send_with_id)
        except Exception:
            log.exception("request.failed", method=method, path=scope["path"])
            if response_started:
                raise
            await error_response(500, "internal_error", "Internal server error.")(
                scope, receive, send_with_id
            )
        finally:
            duration = time.perf_counter() - started
            route = scope.get("route")
            template = getattr(route, "path", _UNMATCHED)
            HTTP_REQUESTS.labels(method, template, str(status_code)).inc()
            HTTP_DURATION.labels(method, template).observe(duration)
            log.info(
                "request.completed",
                method=method,
                path=scope["path"],
                status_code=status_code,
                duration_ms=round(duration * 1000, 1),
            )
            structlog.contextvars.clear_contextvars()


def _reject_body(method: str, path: str, headers: Headers) -> ASGIApp | None:
    """413 on a declared oversize body, 415 on a non-JSON write (01-api-contract §0)."""
    if method not in _WRITE_METHODS or not path.startswith("/api/"):
        return None
    length = headers.get("content-length")
    if length is not None and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return error_response(413, "payload_too_large", "Request body exceeds 64 KiB.")
    media_type = headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        return error_response(
            415, "unsupported_media_type", "Content-Type must be application/json."
        )
    return None
