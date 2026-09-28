"""OllamaTriage over a mocked transport (T-M5-009). No test needs an Ollama container."""

import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain.enums import ErrorClass, TriagedBy
from app.providers.triage.base import ProviderHTTPError
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.pipeline import TriagePipeline
from app.providers.triage.prompt import OPEN
from tests.fakes import MemoryOutcomes, MemoryTriageCache

GOOD = {"category": "roads", "priority": "low", "summary": "roads: pothole", "confidence": 0.7}
Handler = Callable[[httpx.Request], httpx.Response]


def ollama(handler: Handler) -> tuple[OllamaTriage, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    settings = Settings(database_url="x", redis_url="y", triage_provider="ollama")
    return OllamaTriage(settings, transport=httpx.MockTransport(record)), seen


def reply(content: str) -> Handler:
    body = {"model": "llama3.2:1b", "message": {"role": "assistant", "content": content}}
    return lambda _: httpx.Response(200, json=body)


async def test_request_shape_matches_the_groq_path() -> None:
    provider, seen = ollama(reply(json.dumps(GOOD)))
    result = await provider.triage("Single pothole near bus stop", "Bahadurabad")
    assert result.category.value == "roads" and provider.name == "llm:ollama"
    request = seen[0]
    assert str(request.url) == "http://ollama:11434/api/chat"  # service DNS name (BR-SEC-004)
    body = json.loads(request.content)
    assert body["model"] == "llama3.2:1b" and body["format"] == "json"
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0, "num_predict": 200}
    assert OPEN in body["messages"][1]["content"]


async def test_fenced_reply_is_unwrapped() -> None:
    provider, _ = ollama(reply("```json\n" + json.dumps(GOOD) + "\n```"))
    assert (await provider.triage("Single pothole", "Saddar")).priority.value == "low"


@pytest.mark.parametrize(
    "content", ["It is a roads complaint.", json.dumps(GOOD | {"priority": "urgent"}), ""]
)
async def test_bad_reply_is_a_validation_error(content: str) -> None:
    provider, _ = ollama(reply(content))
    with pytest.raises(ValidationError):
        await provider.triage("Single pothole", "Saddar")


@pytest.mark.parametrize("status", [404, 500, 503])
async def test_http_status_becomes_provider_http_error(status: int) -> None:
    """404 is what Ollama answers when the model was never pulled into the volume."""
    provider, _ = ollama(lambda _: httpx.Response(status, json={"error": "model not found"}))
    with pytest.raises(ProviderHTTPError) as exc:
        await provider.triage("Single pothole", "Saddar")
    assert exc.value.status_code == status


async def test_timeout_becomes_timeout_error() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    provider, _ = ollama(slow)
    with pytest.raises(TimeoutError):
        await provider.triage("Single pothole", "Saddar")


async def _no_sleep(_: float) -> None:
    return None


@pytest.mark.parametrize(
    ("status", "calls", "error_class"),
    [(503, 2, ErrorClass.SERVER_ERROR), (404, 1, ErrorClass.OTHER)],
)
async def test_through_the_pipeline(status: int, calls: int, error_class: ErrorClass) -> None:
    provider, seen = ollama(lambda _: httpx.Response(status, json={}))
    pipeline = TriagePipeline(
        provider,
        MemoryTriageCache(),
        MemoryOutcomes(),
        timeout_seconds=5,
        prompt_version="v1",
        sleep=_no_sleep,
    )
    outcome = await pipeline.run("Single pothole near bus stop", "Saddar")
    assert len(seen) == calls
    assert outcome.triaged_by is TriagedBy.RULES_FALLBACK and outcome.error_class is error_class
