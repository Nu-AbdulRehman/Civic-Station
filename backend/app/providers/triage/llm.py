"""LLMTriage: Groq through its OpenAI-compatible endpoint (AD-006, AD-045, FR-AI-005/011).

Retry, timeout and fallback are NOT here: they live once, in pipeline.py. This class makes one
call and turns every outcome into a validated TriageResult or a vendor-neutral exception.
The API key never appears in a log line, an exception message or a metric (BR-TRIAGE-014).
"""

import re
from typing import cast

import httpx2
import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import Settings
from app.domain.models import TriageResult
from app.providers.triage.base import ProviderHTTPError
from app.providers.triage.prompt import build_messages

# Parsing, not repair: a fenced block is unwrapped, and whatever is inside is validated as-is.
_FENCE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def strip_fence(content: str) -> str:
    match = _FENCE.match(content)
    return match.group(1) if match else content


def _retry_after(error: openai.APIStatusError) -> float | None:
    value = error.response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None  # an HTTP-date form falls back to the pipeline's jitter


class LLMTriage:
    name = "llm:groq"

    def __init__(self, settings: Settings, http_client: httpx2.AsyncClient | None = None) -> None:
        """`http_client` exists for tests to inject a mock transport; the SDK client itself,
        and its retry and timeout settings, are always the production ones."""
        if settings.groq_api_key is None:  # Settings already refuses this; belt and braces
            raise SystemExit("GROQ_API_KEY is required when TRIAGE_PROVIDER=llm")
        self._model = settings.triage_model
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key.get_secret_value(),
            base_url=settings.groq_base_url,
            timeout=settings.triage_timeout_seconds,
            max_retries=0,  # the pipeline owns the single retry (BR-TRIAGE-007)
            http_client=http_client,
        )

    async def triage(self, text: str, location: str) -> TriageResult:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=cast(list[ChatCompletionMessageParam], build_messages(text, location)),
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=200,
            )
        except openai.APITimeoutError as exc:
            raise TimeoutError("provider timed out") from exc
        except openai.APIStatusError as exc:
            raise ProviderHTTPError(exc.status_code, _retry_after(exc)) from None
        content = response.choices[0].message.content or ""
        # Requesting JSON is not evidence that JSON came back (BR-TRIAGE-003).
        return TriageResult.model_validate_json(strip_fence(content))
