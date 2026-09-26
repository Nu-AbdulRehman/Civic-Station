"""CORS from CORS_ALLOW_ORIGINS, outermost, so every response carries it (FR-BE-012).

Outermost is load-bearing: if CORS sat inside the request middleware, a 429 or 413 produced
further out would carry no CORS headers and the browser would report an opaque CORS failure
instead of the status the server actually sent (contract test 27).
"""

import structlog
from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.errors import error_response
from app.observability.middleware import resolve_request_id

ALLOWED_METHODS = ["GET", "POST", "PATCH", "OPTIONS"]
ALLOWED_HEADERS = ["Content-Type", "X-Request-ID"]
EXPOSED_HEADERS = ["X-Request-ID", "X-Cache", "Retry-After", "Location"]


class ContractCORSMiddleware(CORSMiddleware):
    """Starlette answers a good preflight with 200 and a refused one with a plain-text 400; the
    contract says 204 and 403 with the error envelope (01-api-contract §0, contract test 26)."""

    def preflight_response(self, request_headers: Headers) -> Response:
        response = super().preflight_response(request_headers)
        if response.status_code == 200:
            return Response(status_code=204, headers=dict(response.headers))
        # Preflights never reach the request middleware, so bind an id for the envelope here.
        request_id = resolve_request_id(request_headers.get("x-request-id"))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        refused = error_response(403, "cors_forbidden", "Origin, method or header not allowed.")
        refused.headers["X-Request-ID"] = request_id
        return refused
