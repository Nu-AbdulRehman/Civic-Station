"""The fixed metric set (00-conventions §6, FR-BE-009). Names and labels do not change casually."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25)

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP requests", ["method", "path_template", "status"]
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path_template"],
    buckets=BUCKETS,
)
TRIAGE_DURATION = Histogram(
    "triage_duration_seconds", "Triage duration", ["provider"], buckets=BUCKETS
)
TRIAGE_FALLBACK = Counter(
    "triage_fallback_total", "Triage fallbacks", ["from_provider", "error_class"]
)
TRIAGE_CACHE_HITS = Counter("triage_cache_hits_total", "Triage cache hits")
TRIAGE_CACHE_MISSES = Counter("triage_cache_misses_total", "Triage cache misses")
STATS_CACHE_HITS = Counter("stats_cache_hits_total", "Stats cache hits")
STATS_CACHE_MISSES = Counter("stats_cache_misses_total", "Stats cache misses")
RATE_LIMIT_REJECTED = Counter("rate_limit_rejected_total", "Submissions rejected by rate limit")
RATE_LIMITER_UNAVAILABLE = Counter(
    "rate_limiter_unavailable_total", "Rate limiter fail-open events (AD-008)"
)

router = APIRouter(tags=["ops"])


@router.get("/metrics", response_class=Response)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
