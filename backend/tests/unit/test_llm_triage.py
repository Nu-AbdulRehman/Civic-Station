"""LLMTriage over a mocked HTTP transport (T-M5-008). No test ever reaches Groq (NFR-TEST-001)."""

import io
import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain.enums import ErrorClass, TriagedBy
from app.observability.logging import configure_logging
from app.providers.triage.base import ProviderHTTPError
from app.providers.triage.llm import LLMTriage, strip_fence
from app.providers.triage.pipeline import TriagePipeline
from app.providers.triage.prompt import OPEN
from tests.fakes import MemoryOutcomes, MemoryTriageCache

KEY = "gsk_SENTINEL_d3adb33f_never_log_me"
GOOD = {"category": "water", "priority": "high", "summary": "water: main burst", "confidence": 0.9}

Handler = Callable[[httpx2.Request], httpx2.Response]


def completion(content: str) -> dict[str, Any]:
    return {
        "id": "c1",
        "object": "chat.completion",
        "created": 0,
        "model": "llama-3.1-8b-instant",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


def llm(handler: Handler) -> tuple[LLMTriage, list[httpx2.Request]]:
    seen: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    settings = Settings(database_url="x", redis_url="y", triage_provider="llm", groq_api_key=KEY)
    transport = httpx2.AsyncClient(transport=httpx2.MockTransport(record))
    return LLMTriage(settings, http_client=transport), seen


def reply(content: str) -> Handler:
    return lambda _: httpx2.Response(200, json=completion(content))


async def test_request_shape_is_fixed() -> None:
    provider, seen = llm(reply(json.dumps(GOOD)))
    result = await provider.triage("Water main burst on Street 12", "Saddar")
    assert result.category.value == "water" and provider.name == "llm:groq"
    body = json.loads(seen[0].content)
    assert body["model"] == "llama-3.1-8b-instant"
    assert body["response_format"] == {"type": "json_object"}
    assert (body["temperature"], body["max_tokens"]) == (0, 200)
    assert OPEN in body["messages"][1]["content"]
    assert str(seen[0].url).startswith("https://api.groq.com/openai/v1/")


async def test_fenced_json_is_unwrapped() -> None:
    provider, _ = llm(reply("```json\n" + json.dumps(GOOD) + "\n```"))
    assert (await provider.triage("Water main burst", "Saddar")).priority.value == "high"


@pytest.mark.parametrize(
    "content",
    [
        "Sure! This looks like a water complaint with high priority.",  # prose
        json.dumps(GOOD | {"category": "plumbing"}),  # out of enum
        json.dumps(GOOD | {"summary": "x" * 400}),  # 400-character "one line"
        json.dumps(GOOD | {"confidence": 1.5}),
        '```json\n{"category": "water"}\n```',  # fenced but incomplete
        "",
    ],
)
async def test_bad_output_is_a_validation_error(content: str) -> None:
    provider, _ = llm(reply(content))
    with pytest.raises(ValidationError):
        await provider.triage("Water main burst", "Saddar")


@pytest.mark.parametrize(
    ("status", "headers", "retry_after"),
    [(429, {"retry-after": "3"}, 3.0), (429, {}, None), (500, {}, None), (400, {}, None),
     (401, {}, None)],
)  # fmt: skip
async def test_http_errors_become_provider_http_errors(
    status: int, headers: dict[str, str], retry_after: float | None
) -> None:
    provider, _ = llm(lambda _: httpx2.Response(status, headers=headers, json={"error": {}}))
    with pytest.raises(ProviderHTTPError) as exc:
        await provider.triage("Water main burst", "Saddar")
    assert (exc.value.status_code, exc.value.retry_after_seconds) == (status, retry_after)
    assert KEY not in str(exc.value)


async def test_transport_timeout_becomes_timeout_error() -> None:
    def hang(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    provider, _ = llm(hang)
    with pytest.raises(TimeoutError):
        await provider.triage("Water main burst", "Saddar")


async def _sleep(_: float) -> None:
    return None


@pytest.mark.parametrize(
    ("handler", "calls", "error_class"),
    [
        (lambda _: httpx2.Response(500, json={}), 2, ErrorClass.SERVER_ERROR),
        (lambda _: httpx2.Response(429, json={}), 2, ErrorClass.RATE_LIMITED),
        (lambda _: httpx2.Response(401, json={}), 1, ErrorClass.OTHER),
        (reply("not json at all"), 1, ErrorClass.VALIDATION_FAILED),
    ],
)
async def test_through_the_pipeline_with_the_key_never_logged(
    handler: Handler, calls: int, error_class: ErrorClass
) -> None:
    """NFR-SEC: forced 401/500/429/bad output; the key appears in no log line, no exception
    text, and the SDK's own retries are off, so the call count is the pipeline's alone."""
    buffer = io.StringIO()
    configure_logging("DEBUG", stream=buffer)
    provider, seen = llm(handler)
    pipeline = TriagePipeline(
        provider,
        MemoryTriageCache(),
        MemoryOutcomes(),
        timeout_seconds=5,
        prompt_version="v1",
        sleep=_sleep,
    )
    outcome = await pipeline.run("Water main burst on Street 12", "Saddar")
    assert outcome.triaged_by is TriagedBy.RULES_FALLBACK and outcome.error_class is error_class
    assert len(seen) == calls
    assert KEY not in buffer.getvalue()


def test_strip_fence_leaves_plain_json_alone() -> None:
    assert strip_fence('{"a": 1}') == '{"a": 1}'
    assert strip_fence('```\n{"a": 1}\n```') == '{"a": 1}'
