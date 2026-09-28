"""OllamaTriage: the fully offline path, same interface as LLMTriage (AD-006, FR-AI-002).

Runs against the `ollama` service on the `internal` network, which has no egress: the weights
must already be in the `ollama_models` volume (`make pull-models`, AD-046). Same prompt, same
JSON mode, same validation; retry, timeout and fallback stay in pipeline.py.
"""

import httpx

from app.config import Settings
from app.domain.models import TriageResult
from app.providers.triage.base import ProviderHTTPError
from app.providers.triage.llm import strip_fence
from app.providers.triage.prompt import build_messages


class OllamaTriage:
    name = "llm:ollama"

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """`transport` exists for tests to inject a mock; the client settings are production's."""
        self._model = settings.ollama_model
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.triage_timeout_seconds,
            transport=transport,
        )

    async def triage(self, text: str, location: str) -> TriageResult:
        payload = {
            "model": self._model,
            "messages": build_messages(text, location),
            "format": "json",  # AD-045: JSON mode, the same mechanism as the Groq path
            "stream": False,
            "options": {"temperature": 0, "num_predict": 200},
        }
        try:
            response = await self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise TimeoutError("provider timed out") from exc
        if response.status_code >= 400:
            raise ProviderHTTPError(response.status_code)
        content = response.json().get("message", {}).get("content", "")
        return TriageResult.model_validate_json(strip_fence(content))

    async def aclose(self) -> None:
        await self._client.aclose()
