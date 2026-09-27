# ADR-0001 — The triage provider interface

- **Status:** Accepted
- **Date:** 2026-09-16 (accepted). Revised 2026-09-25 by the specification audit.
- **Decides:** `AD-005`, `AD-006`, `AD-007`, `AD-009`
- **Related requirements:** `FR-AI-001`, `FR-AI-002`, `NFR-ARCH-002`, `BR-TRIAGE-002`, `BR-TRIAGE-005`

## Context

The system classifies free-text municipal complaints into a category, a priority and a one-line summary. The classifier is the part of the system most likely to change: today a keyword rule, tomorrow a hosted language model, next year a fine-tuned classifier. It is also the part least under our control — a free-tier hosted model is rate-limited, occasionally slow, and occasionally wrong in ways that are syntactically valid.

The engineering problem is therefore not "call a model". It is: make the rest of the system indifferent to which classifier is running, and make it survive the classifier being unavailable.

A naive design calls the vendor SDK from the submission service. That couples the business flow to a vendor, makes tests require a network, makes CI non-deterministic, and means a provider outage becomes a 500 for a citizen reporting a flooded street.

## Decision

**Define a `TriageProvider` protocol and a `TriageResult` Pydantic model. Every classifier implements the protocol. The submission service depends only on the protocol. The concrete implementation is chosen at startup from the `TRIAGE_PROVIDER` environment variable by a factory.**

```
TriageResult:   category: Category | priority: Priority | summary: str(≤140) | confidence: float(0..1)
TriageProvider: name: str ; async triage(text, location) -> TriageResult
```

**`triage` is `async`.** `AD-005` fixes a fully async stack — async routes, SQLAlchemy async engine, `httpx.AsyncClient`, `redis.asyncio` — and on that stack a synchronous `triage` is a different contract, not a cosmetic variation: it would block the event loop for up to 10 seconds per call, which is the exact failure `AD-004` relies on not happening. The brief's §2.5 sketch shows a synchronous `def`; this is a deliberate departure from the sketch, in the direction the rest of the brief requires.

Four implementations:

| Implementation | `TRIAGE_PROVIDER` | Purpose |
|---|---|---|
| `LLMTriage` | `llm` | Production path. Groq `qwen/qwen3.8-27b`, via the OpenAI-compatible endpoint using the official `openai` SDK with `base_url` changed. Reports `triaged_by = "llm:groq"`. |
| `OllamaTriage` | `ollama` | Fully offline path. `llama3.2:1b` in a container in the Compose stack. Reports `"llm:ollama"`. |
| `RuleBasedTriage` | `rules` | Deterministic keyword classifier. No network. Never raises. Reports `"rules"`, or `"rules:fallback"` when reached through the fallback path. |
| `SimulatedTriage` | `simulated` | Seeded deterministic fake for CI, with configurable failure injection. Reports `"simulated"`. |

**`"simulated"` is a legal `triaged_by` value** (`AD-020`), in the database `CHECK` and in the API enum. CI runs `TRIAGE_PROVIDER=simulated`, so a successful CI triage has to persist something; recording it truthfully keeps the fallback-rate measurement honest, which having it masquerade as `"rules"` would not.

**The resilience pipeline wraps the provider, not the other way round.** It is a single orchestration point that applies, in order:

1. **Redact** the complaint text (`AD-003`, `ADR-0004`) — first, because everything downstream, including the cache key, is computed on the redacted form.
2. **Content-hash cache lookup** on `SHA-256` of normalised redacted text + location + provider name + `PROMPT_VERSION` (`AD-019`).
3. **Provider call** under a hard 10-second timeout.
4. **At most one jittered retry**, only on timeout / 429 / 5xx, honouring `Retry-After` up to 5 seconds.
5. **Pydantic validation** of the result.
6. **On any failure, `RuleBasedTriage`** with `triaged_by = "rules:fallback"`, one `WARNING`, and the fallback counter incremented.

Step 1 was missing from the first version of this ADR, which made the document disagree with `ADR-0004` about whether redaction happens at all, and left the cache key ambiguous about which form of the text it hashes.

Supporting decisions taken here:

- **An unknown `TRIAGE_PROVIDER` value fails fast at startup.** Silently defaulting to a provider the operator did not ask for is worse than not booting.
- **A schema-validation failure is not re-prompted.** It falls through to rules. The resulting fallback rate is then an honest measurement of prompt quality rather than a number hidden behind a retry.
- **Recent triage outcomes live in a Redis list**, trimmed to 20, so `/api/meta/providers` answers globally rather than per-pod once the HPA has scaled out.

## Alternatives considered

**Call the SDK directly from the service.** Fewer files. Rejected: it makes the vendor a dependency of the business rule, makes every test need a network or a monkeypatch that reaches past the seam, and leaves no place to put the timeout, retry and fallback logic other than inside the business flow.

**An abstract base class instead of a `Protocol`.** Rejected in favour of a `Protocol` because implementations need no import of the interface module, which keeps the dependency arrow pointing one way and makes a test double a plain class rather than a subclass.

**Retry with a second model on failure, rather than falling back to rules.** Rejected: a second hosted model is a second thing that can be rate-limited at the same moment, usually by the same cause. The fallback must have no network dependency at all or it is not a fallback.

**Put the timeout/retry logic inside each provider.** Rejected: it would be duplicated four times and the behaviour would drift. It lives once, in the orchestration layer, where all callers route through it.

## Consequences

**Good.**
- Swapping the classifier is an environment variable. No service, route or repository imports a concrete provider class — verifiable by grep, which is how `NFR-ARCH-002` is checked.
- CI is deterministic by construction: it pins `TRIAGE_PROVIDER=simulated` and injects failure rather than hoping a live provider misbehaves on cue.
- The mandatory test — "a provider that always raises still yields 201 and `triaged_by == rules:fallback`" — is ordinary dependency injection, not mocking internals.
- Timeout, retry and fallback exist in exactly one place, so they can only be wrong once.

**Costs.**
- Four implementations to build and keep working, plus a factory, for a system that in production runs one of them.
- `RuleBasedTriage` carries a hard obligation: it must never raise, for any input. If the fallback can fail, there is no fallback. It is tested against adversarial inputs for this reason.
- `triaged_by` must be recorded accurately by every path. A wrong value makes the entire observability surface a lie and invalidates the fallback demonstration.

**Follow-on obligations.**
- `docs/TRIAGE.md` records the prompts, the measured latency per provider, the cache hit rate, and the measured fallback rate.
- The provider name is part of the triage cache key (`AD-019`), so switching providers cannot serve results produced by the previous one.
