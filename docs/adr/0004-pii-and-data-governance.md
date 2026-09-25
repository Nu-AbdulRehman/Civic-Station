# ADR-0004 — PII and data governance in the triage path

- **Status:** Accepted
- **Date:** 2026-09-16 (accepted). Revised 2026-09-25 by the specification audit.
- **Decides:** `AD-003`
- **Related requirements:** `NFR-PRIV-001`, `NFR-PRIV-002`, `NFR-PRIV-003`, `BR-TRIAGE-015`, `FR-AI-011`

## Context

Civic-Station asks citizens to describe a municipal problem in free text and to optionally leave contact details. Real complaints in this domain contain personal data as a matter of course: *"burst main outside House 42, Street 12, my mother is on the ground floor, call me on 0300-1234567"*. The location field is, by design, a real address. The `reporter_contact` field is, by design, a phone number or an email address.

To classify a complaint we send text to a third party. The free tiers that make this project possible are free for a reason, and the terms differ:

- **Groq** (the chosen primary, `AD-006`) offers a free developer tier with no credit card, gated by rate limits.
- **Google AI Studio's** free Gemini tier states that inputs may be used to improve Google's models.

Three facts have to be reconciled: the data is personal, the processor is a third party, and the citizen did not choose the processor and is not being asked to consent to it.

The honest framing is that "we are students and it is free" is not a data-governance position. Whatever we do, we should be able to say precisely what left the machine, to whom, and why that was acceptable.

## Decision

**Minimise before sending, and state the residual risk.**

1. **`reporter_contact` never leaves the process.** It is not needed to classify a complaint — the category and priority are determined by what happened and where, not by who reported it. It is excluded from the prompt payload structurally: the provider function does not receive it as a parameter, rather than receiving it and choosing not to use it.

2. **Only `text` and `location` are sent**, and `text` is redacted first. A `redact()` function removes, before prompt construction:
   - phone numbers (including the local `03xx-xxxxxxx` shape),
   - email addresses,
   - long digit sequences (CNIC-shaped and account-shaped runs).
   Each is replaced with a stable placeholder token (`[PHONE]`, `[EMAIL]`, `[NUMBER]`) so the sentence still parses and classification quality is not damaged by leaving a hole.

3. **`location` is sent unredacted.** This is a deliberate exception and the main residual exposure. A street address materially improves classification — "Street 12" versus "Sector G-11 main road" distinguishes a household problem from an arterial one — and the location is not by itself identifying in the way a name plus a phone number is. Removing it would degrade the product's core function.

4. **Redaction happens before hashing.** The triage cache key is computed on the redacted text (`AD-019`), so the cache and the prompt see the same content and redaction cannot silently disable caching.

5. **The API key is environment-only.** From `.env` locally, a Kubernetes Secret on the cluster, a GitHub Secret in CI. Never logged, never in an error message, never in a response body, never committed. Base64 in a manifest is encoding, not encryption, and does not count as protection.

6. **Nothing is sent at all on the offline path.** `OllamaTriage` runs a model in a container on the `internal` network with no egress. Selecting `TRIAGE_PROVIDER=ollama` makes this ADR's exposure zero, at a measured cost in classification quality that is reported in `docs/TRIAGE.md`.

## What actually leaves the machine

| Data | Sent to Groq | Stored locally |
|---|---|---|
| Complaint text | **Yes**, redacted of phone numbers, emails and long digit runs | Yes, in full, unredacted |
| Location | **Yes**, in full | Yes |
| `reporter_contact` | **No** | Yes |
| Complaint id, timestamps, status | **No** | Yes |
| Any operator or system credential | **No** | Environment only |

## Alternatives considered

**Send everything and document it.** Cheapest, and defensible if the terms are stated. Rejected: the redaction is roughly twenty lines and one test, and shipping the weaker option to save that is not a trade-off worth defending.

**Redact the location too.** Rejected on function: the location is classification signal, not incidental metadata. Removing it would make the system worse at the thing it exists to do, and the exposure is materially lower than a name-plus-number pair.

**Use Gemini for the generous free quota.** Rejected for this project given that the free tier may use inputs to improve models — that is a materially different commitment to make on a citizen's behalf than rate-limited inference. Groq's tier is gated by rate limits rather than by a data-for-service exchange.

**Ollama only, nothing leaves.** The strongest privacy position, explicitly costs no marks, and remains available as a runtime choice. Not made the default because measuring the hosted-versus-self-hosted trade-off is part of what the project is supposed to teach — and that measurement requires actually running both.

## Consequences

**Good.**
- The exposure is bounded and describable in one table.
- The decision is implemented in code, not only asserted in a document: `redact()` has a unit test, and a test asserts that the payload sent to the provider contains no contact field.
- Switching to the zero-egress path is an environment variable, so the mitigation for a change in provider terms already exists and is already tested. **This mitigation depends on `OllamaTriage` remaining in the build**, which `AD-012` originally listed as the fourth item in a cut order — cutting it would have quietly deleted the fallback this ADR relies on. `AD-012` was revised on 2026-09-25 to remove it; `FR-AI-002` now requires all four providers.

**Costs and limits — stated plainly.**
- **Regex redaction is not PII removal.** It catches formatted identifiers. It will not catch a name written in prose ("tell Asif at number 42"), an unusual phone format, or an address embedded mid-sentence. The system reduces exposure; it does not eliminate it, and claiming otherwise would be worse than not redacting at all.
- **Location is still sent**, and combined with an unredacted local copy it is the most identifying thing that leaves.
- **The citizen is not consulted.** There is no consent flow, no privacy notice on the submission form, and no data-retention policy. In a real municipal deployment all three would be required before this system could take a single complaint, and their absence here is a scope decision, not an oversight. **Recorded as such in `docs/NON-GOALS.md`**, with what each would take — previously this paragraph named the gap and nothing carried it forward, so the obligation existed only inside an ADR nobody was required to re-read.
- **Retention is indefinite and there is no delete path.** `FR-DATA-002` states this explicitly in the schema: rows are kept forever and no endpoint removes one. A citizen who asks for their complaint to be deleted cannot be served by this system. The data most affected is `reporter_contact`, which is exactly the column this ADR keeps out of the model payload — so it is protected in transit and not in storage, and saying so is more useful than implying otherwise.
- **The operator is not authenticated.** `PATCH /api/complaints/{id}/status` is open to any caller (`AD-056`), so anyone can resolve or reject any citizen's complaint. This is out of scope for the assignment and is recorded in `docs/NON-GOALS.md`; it is a governance limitation as much as a security one, and it belongs in the same list as the three above.
- **Redaction slightly degrades classification input**, which is why the placeholders are typed (`[PHONE]` rather than a blank) — measured and reported rather than assumed.

**Follow-on obligations.**
- `docs/TRIAGE.md` reports the measured quality difference between Groq and Ollama, which is the empirical half of this decision.
- If the provider changes, this ADR is revisited before the provider is switched, not after.
