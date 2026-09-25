# Specification audit — `docs/` against the problem statement

**Status:** Audit output, **remediated 2026-09-25.** The findings below are preserved as written; the remediation is summarised in the next section and reflected in the documents themselves. Line numbers in citations are as of the audit and have since moved.
**Audited:** 27 files under `docs/` (requirements, business rules, module map, rubric
traceability, the 44-decision resolution log, 13 design documents, 4 ADRs, 3 schedule
documents), against `docs/planning/Civic-Station_Problem_Statement.md` as the source of
truth.
**Date of audit:** 2026-09-25.

## Remediation summary

All 136 defects were addressed on 2026-09-25. The four decisions that needed a human were taken by both developers:

| Decision | Chosen | Recorded in |
|---|---|---|
| `triaged_by` for a successful `SimulatedTriage` | Add `simulated` to the enum and the `CHECK`, so the column records what actually ran | `AD-020` |
| Two networks or three | **Three**, keeping the named `egress` network; `FR-CTR-005` and `RUB-G-03` updated to match, deviation recorded | `AD-002`, `ADR-0005` |
| `GET /api/version` and the build-time SHA | **Keep the endpoint, inject `APP_VERSION` at runtime** — resolves the endpoint count and the build-once-deploy-many conflict together | `AD-014`, `AD-034` |
| Authentication on operator actions | **Explicit non-goal**, documented with its exposure and attachment point | `AD-056`, `docs/NON-GOALS.md` |

**What changed structurally.** Twelve decisions added (`AD-045`–`AD-056`) and eight revised, each marked `[rev 2026-09-25]`. Five requirements added: `FR-BE-029` (`/api/version`), `FR-CACHE-007` (the distributed-limiter proof), `FR-AI-014` (hit rate and latency data sources), `FR-PROC-006` (credential rotation and the incident note), `FR-PROC-007` (obtaining the provider credential). Two documents created: `docs/adr/0005-network-topology-and-limiter-degradation.md` and `docs/NON-GOALS.md`. `FR-LOAD-004` promoted from bonus `SHOULD` to `MUST`. `FR-DATA-003` went from two indexes to three, `FR-DOC-002` from four ADRs to five, `docs/design/01-api-contract.md` from 20 contract tests to 30.

**What was not fixed, deliberately.**

- **The mark total (S1-5).** The brief's section weights sum to 175, not the 150 it states. This is a defect in the brief; `AD-047` records the finding and the action — raise it with the instructor. No document now quotes a total, because either figure would be wrong.
- **Appendix A, the schedule findings.** The schedule documents are not being used. They are left as they are, unremediated, and `docs/README.md` marks them as outside the reading order.
- **Five limitations became documented non-goals** rather than being built: authentication, Kubernetes `NetworkPolicy`, a global provider-spend cap, data retention and deletion, and image signing. Each is in `docs/NON-GOALS.md` with what it leaves open and where the work would attach.

**Two findings in this report were investigated and withdrawn** — the `civic-station.localhost` claim and the unroutable-ops-endpoints claim. Both are recorded in Appendix B so they are not raised again.

---

## How to read this

Defects are banded by how much they cost if left alone:

| Band | Meaning |
|---|---|
| **S1 — Blocker** | Implementation cannot proceed correctly as written, or a marked rubric line or §5.3 deduction is at risk. |
| **S2 — Contradiction** | Two documents state incompatible things. Someone must pick. |
| **S3 — Unfalsifiable** | A `MUST` with no number, unit, threshold or data source. It cannot pass or fail. |
| **S4 — Traceability** | Orphan IDs, unreferenced requirements, broken indexes. Real, cheap, contained. |

Every entry cites `file:line`. Line numbers are as of this audit; they move if the docs
are edited. Appendix B states what was verified by recomputation and what is reported at
lower confidence.

### Counts

| Band | Count |
|---|---|
| S1 — Blocker | 11 |
| S2 — Contradiction | 38 |
| S3 — Unfalsifiable | 68 |
| S4 — Traceability | 19 |
| Deviations from the brief (decisions, not defects) | 6 |
| Appendix A — schedule findings, not actioned | 12 |

### The short list: fix these before writing code

1. `triaged_by` has no legal value for a successful `SimulatedTriage`, and CI runs `simulated` (S1-1). Every CI test that persists a complaint fails the `CHECK`.
2. Decide whether `OPEN-DECISIONS.md` is open or closed (S1-2). Its header and its log disagree, and its own rule gates all 13 design docs on the answer.
3. Pick two networks or three (S1-3). Four marks sit on a rubric line whose own text says two, citing two sources that disagree.
4. Supply CPU and memory `requests` values (S1-6). Without a `requests.cpu` the HPA has no denominator and the 4-mark scale-out evidence is unobtainable.
5. Pin the triage model, write the prompt, write the output schema (S1-8). Rubric F is 25 marks and currently rests on three placeholders.
6. Specify the load profile as numbers (S1-9). No VUs, no durations, no thresholds, and no time-series source for the replicas-vs-load chart the brief requires.

---

## S1 — Blockers

### S1-1 · `triaged_by` has no legal value for a successful `SimulatedTriage`

- `docs/design/01-api-contract.md:37` — "`llm:groq`\|`llm:ollama`\|`rules`\|`rules:fallback`" — the response field domain is exactly four values.
- `docs/design/04-M3-data.md:34` — "`varchar(32)` \| `NOT NULL`, `CHECK (triaged_by IN (...))`" — enforced in the database.
- `docs/design/06-M5-ai-triage.md:99` — "it reports `simulated` internally" — a fifth value.
- `docs/design/09-M8-cicd.md:33` and `docs/design/03-M2-backend.md:175` — CI runs `TRIAGE_PROVIDER=simulated`.

Every CI test that submits a complaint and persists it writes a value the `CHECK`
rejects. Contract test 1 (`01-api-contract.md:248`) asserts `triaged_by` "is one of the
four valid values", which a simulated run cannot satisfy either. The `CHECK` set itself is
written as a literal ellipsis, so the allowed values are unspecified in the document that
owns them.

Three ways out, each with a consequence: add `simulated` to the `CHECK` and to the
contract enum (the frontend then must render a provider it will never see in production);
have `SimulatedTriage` report `rules` (loses the ability to tell a CI row from a real
fallback, which `docs/TRIAGE.md` is supposed to measure); or make the `CHECK` a
non-enumerated constraint. The decision belongs in the resolution log, since `AD-020`
already owns the `triaged_by` representation.

### S1-2 · `OPEN-DECISIONS.md` is simultaneously open and closed

- `docs/decisions/OPEN-DECISIONS.md:3` — "**Status:** Round 1 output — **awaiting human decisions (Round 2)**"
- `docs/decisions/OPEN-DECISIONS.md:20` — "**Resolution log is at the bottom of this file. Fill it in during Round 2.**"
- `docs/decisions/OPEN-DECISIONS.md:298` — "**All decisions are RESOLVED.**"
- `docs/requirements/FUNCTIONAL-REQUIREMENTS.md:13` — "**All 44 decisions are RESOLVED.** Do not re-decide one"

The header was never updated when the log was filled in. This matters beyond tidiness
because of the file's own gate at `:8`: "no design document may be written until the
decisions it depends on are marked RESOLVED here". Read literally, all 13 design documents
and all 4 ADRs were written in violation of it.

Related, same root cause: all four ADRs carry `**Date:** Round 2` in place of a date
(`docs/adr/0001-provider-interface.md:4`, `0002:4`, `0003:4`, `0004:4`), and no row in the
44-decision log records who accepted it or when — despite `:10` insisting "it is not a
decision until a human accepts it" and `:298` requiring "a note of what changed and why"
for any later change. There is no acceptance record to amend.

The ADR-to-decision mapping also disagrees with itself: `:18` maps `AD-005 → ADR-0001`,
while `docs/adr/0001-provider-interface.md:5` claims `AD-005`, `AD-006`, `AD-007` **and**
`AD-009`.

### S1-3 · Two networks or three

- `docs/requirements/FUNCTIONAL-REQUIREMENTS.md:444` (`FR-CTR-005`) — "**MUST.** Compose defines an `edge` network … and an `internal` network … the backend is the only service on both"
- `docs/decisions/OPEN-DECISIONS.md:307` (`AD-002`) — "**Three networks:** `edge` …, `internal` …, `egress`"
- `docs/design/07-M6-containers.md:53` — implements three.
- `docs/requirements/RUBRIC-TRACEABILITY.md:85` (`RUB-G-03`) — "Two networks with `internal: true`; frontend provably cannot reach the DB \| **4** \| FR-CTR-005, BR-SEC-001, **AD-002**"

The 4-mark rubric row cites both the requirement that says two and the decision that says
three. `FR-CTR-005` was never updated after `AD-002` resolved, and `FR-CTR-005` also
assigns Ollama no network at all, while `AD-002` puts it on `internal`.

This is also a deviation from the brief — see the deviation register. The engineering
argument for three is good (`07-M6-containers.md:58`: a named `egress` network states the
intent rather than making outbound capability a side effect of the browser-facing
network). The exposure is that a marker reading `RUB-G-03` sees "two".

### S1-4 · `ai_summary` nullable, against a resolved decision

- `docs/decisions/OPEN-DECISIONS.md:333` (`AD-023`, resolved) — "**`RuleBasedTriage` produces an `ai_summary` too**"
- `docs/design/01-api-contract.md:36` — "≤ 140 characters. Populated on every path including `rules` (`AD-023`)"
- `docs/design/04-M3-data.md:33` — "`ai_summary` \| `text` \| nullable"

The database does not enforce a decision that is already made. Same shape one row down:
`04-M3-data.md:35` has `triage_confidence` nullable while `06-M5-ai-triage.md:92` says the
rules path always sets it.

Compounding it, the rules-path summary algorithm is an example, not a spec
(`06-M5-ai-triage.md:93` — "for example the first clause, truncated to 140 characters,
prefixed with the matched category"), so the guarantee has no implementable definition.

### S1-5 · The rubric does not add up to 150

`docs/requirements/RUBRIC-TRACEABILITY.md:4` — "**Source:** … §4 (150 marks)".

Recomputed from that file's own rows:

| A | B | C | D | E | F | G | H | I | J | Total | Bonus `RUB-X` | Grand |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 18 | 25 | 12 | 10 | 25 | 15 | 20 | 20 | 15 | **175** | 15 | 190 |

The per-section weights match the brief line for line, so the error originates upstream at
`docs/planning/Civic-Station_Problem_Statement.md:389` ("**150 marks.**") and the docs
faithfully inherited it. The brief's §5.1 has the same problem: `:499` calls parts A–G
"110 marks" where the same lines sum to 120.

Consequences inside the docs: every design document's `Delivers:` line is denominated
against a total that does not exist, and two of them claim the same marks —
`docs/design/08-M7-kubernetes.md:5` "Delivers: Rubric H (20 marks)" against
`docs/design/10-M9-load-evidence.md:5` "Delivers: 7 of Rubric H's 20 marks".

This is a defect in the brief, not the docs. The useful action is to raise it with the
instructor rather than silently pick a denominator, because which reading is right changes
what a mark is worth.

### S1-6 · No resource `requests` or `limits` values exist anywhere

- `docs/design/08-M7-kubernetes.md:67` — "Every container declares `resources.requests` and `resources.limits`"
- `docs/design/08-M7-kubernetes.md:71` — "Start with a guess (record it…)"
- `docs/requirements/FUNCTIONAL-REQUIREMENTS.md:515` (`FR-K8S-007`) and `docs/requirements/NON-FUNCTIONAL-REQUIREMENTS.md:291` (`NFR-OPS-005`) — same requirement, no values.

Not one CPU or memory figure appears in any of the 27 documents, for any container. The
brief flags this exact omission as the recurring failure
(`Problem_Statement.md:318`): "With no `resources.requests.cpu` on your pods there is no
denominator, and the HPA sits at `<unknown>/60%` forever. Every semester, several teams
debug a 'broken HPA' that is in fact a missing three-line block."

`RUB-H-04` puts 2 marks on requests and limits being set, and `RUB-H-05` puts 4 marks on
captured HPA scale-out that is impossible without them. The VPA loop
(`RUB-H-06`, 3 marks) requires a recorded initial guess to compare the recommendation
against — `08-M7-kubernetes.md:71` asks for that recording but supplies no starting value,
so step 1 of the five-step loop at `Problem_Statement.md:332` has no input.

The dev and prod overlays also specify no values (`08-M7-kubernetes.md:130` — "lower
replicas/resources, dev ConfigMap values"), and the HPA's `minReplicas: 2`
(`:76`) overrides any lowered dev replica count, so the dev overlay's stated behaviour
cannot occur.

### S1-7 · No index serves the query the API actually issues

- `docs/design/01-api-contract.md:98` — `category`, `priority`, `status` are optional and combinable filters.
- `docs/design/01-api-contract.md:111` — "**Default order is `created_at DESC, id DESC`** (`AD-016`) … without it, pagination can return the same row on two pages."
- `docs/design/04-M3-data.md:52` — `ix_complaints_created_at` on `(created_at DESC)`.
- `docs/design/04-M3-data.md:53` — `ix_complaints_status_priority` on `(status, priority)`.

The real query filters on some subset of three columns and orders by two. The
`created_at` index cannot apply the filter; the `(status, priority)` index cannot serve the
order. Nothing indexes `category`, though it is a first-class filter. The `created_at`
index also omits the `id` tie-break that the stable-pagination guarantee at `:111` rests
on.

`RUB-D-03` marks 2 marks on "Two indexes, each justified by a named query", and
`FR-DATA-003` (`FUNCTIONAL-REQUIREMENTS.md:317`) requires "The named query appears in the
repository layer and its shape matches the index" — which, as specified, it will not.

### S1-8 · The AI layer has no model, no prompt and no output schema

Rubric F is 25 marks, the largest single block, and it currently rests on placeholders.

- `docs/design/00-conventions.md:92` — "`TRIAGE_MODEL` \| `(small instruct model)` \| M5.2 \| Pinned by name…" — described as pinned, while the value is a parenthetical.
- `docs/design/00-conventions.md:94` — "`OLLAMA_MODEL` \| `(1B-class model)`" — same.
- `docs/design/06-M5-ai-triage.md:118` — the prompt is described (delimiters, a system prompt that constrains output) but its text exists nowhere; `docs/design/11-M10-documentation.md:88` defers "The prompt(s), verbatim" to `docs/TRIAGE.md`, which does not exist.
- `docs/design/06-M5-ai-triage.md:69` — "Structured output requested via JSON mode **or** a response schema" — two mechanisms with different request shapes and different failure modes, neither selected.

No `temperature`, no `max_tokens` and no `seed` are specified, so the production path is
unconstrained in cost and output length and nothing makes it repeatable.

There is no cost cap of any kind: no per-day or per-hour inference budget, no token
budget, no quota counter and no circuit breaker. A provider that starts returning 429 or
timing out pays the full 10 s timeout plus a retry on every request, indefinitely
(`06-M5-ai-triage.md:51`). The retry also ignores the provider's `Retry-After`
(`:60`), and the jitter has no stated bound.

The brief's cost argument (`Problem_Statement.md:138`: "one bored user with a for loop
exhausts your entire day's quota") is answered only by a per-IP limiter of 10 requests per
60 seconds (`docs/design/05-M4-cache.md:50`). Ten IPs legally exceed the provider quota;
no document bounds aggregate spend.

### S1-9 · The load profile is entirely unspecified

- `docs/design/10-M9-load-evidence.md:27` — "Stage profile: a ramp …, a plateau above the 60 % target …, then a drop to zero" — no VUs, no stage durations, no request mix, no k6 `thresholds` block.
- `docs/requirements/FUNCTIONAL-REQUIREMENTS.md:616` — "a real load test drives scale-out" — "real" is not a criterion.
- `docs/design/10-M9-load-evidence.md:103` — "`hpa-watch.txt` shows 2 → higher → back to 2" — no target replica count, no time bound, no latency or error-rate ceiling.

There is no machine-checkable pass or fail for the run that `RUB-H-05` (4 marks) and
`RUB-X-01` (+4) both depend on. The only numeric threshold in the module —
"the failed-request count, which must be zero" (`:81`) — belongs to the bonus scenario,
not the marked evidence.

Worse, the chart has no data source. The brief requires "a chart of replicas against
offered load **over time**" (`Problem_Statement.md:320`), and `AD-044`
(`OPEN-DECISIONS.md:359`) names "the captured `hpa -w` output and the k6 summary" as the
inputs. A k6 *summary* is an aggregate, not a time series, and `kubectl get hpa -w` emits
no timestamps — so neither axis of the required chart has a source, and the HPA-lag figure
that `NFR-SCALE-...:198` and engineering-notes Q5 both demand in seconds cannot be
derived from the stated evidence.

### S1-10 · `PATCH /api/complaints/{id}/status` has no authentication or authorisation

The brief calls this an operator action (`Problem_Statement.md:59`: "Operator can advance
status"). No requirement, design document or ADR authenticates or authorises anyone.
`docs/design/01-api-contract.md` contains no auth statement at all, and
`docs/design/02-M1-frontend.md:69` offers every transition to any visitor.

Stated plainly: **the brief does not ask for auth either.** Its API table
(`Problem_Statement.md:81–93`) has no auth column and the rubric has no auth line. So this
is a scope question, not a missed requirement — but it is worth answering deliberately,
because "any visitor can resolve any complaint" is the first thing a viva will ask about,
and the honest answer ("out of scope, and here is where it would go") is a better answer
than not having noticed.

Two related gaps sit in the same place: there is no operator entity in the data model at
all, and no status-transition history, so `updated_at` is the only trace that a state
change ever happened (`docs/design/04-M3-data.md:24`).

### S1-11 · Two prerequisites that no requirement or design document owns

Both survive the schedule being discarded, because neither is a scheduling problem.

**Credential rotation and the incident note.** `Problem_Statement.md:520` attaches to a
leaked secret "**−20**, plus you must rotate the credential and write an incident note".
No requirement, design document or ADR defines a rotation procedure or an incident note.
`docs/design/07-M6-containers.md:133` only scans history for leaks, and
`docs/design/08-M7-kubernetes.md:121` provisions secrets with no rotation path and no
statement of what happens to running pods when a secret changes. The only occurrences of
"incident" in the doc set are in `docs/adr/0003-deploy-by-sha.md:12,30`, about rollback.

**Obtaining the API key.** `docs/design/09-M8-cicd.md:77` assumes "`GROQ_API_KEY` is a
repository secret". No document covers signing up
(`Problem_Statement.md:174`: "Sign up at console.groq.com with an email"), checking the
live rate limits, or provisioning the GitHub Secret in the first place — while
`AD-006` (`OPEN-DECISIONS.md:311`) leaves "Live rate limits **must be checked** on the
provider's page and cited with the date seen" as an open action item inside a row marked
RESOLVED, with no owner and no requirement to land it. The rate-limit number chosen in
`AD-017` is therefore unsized against any real quota.

---

## S2 — Contradictions

Both citations given. "Should change" is a suggestion, not a decision.

| # | Defect | Citation A | Citation B | Should change |
|---|---|---|---|---|
| 1 | `/api/stats` returns counts by status, or not | `AD-025`, `OPEN-DECISIONS.md:335` "by category, by priority, by status, plus a total" | `FR-BE-005`, `FUNCTIONAL-REQUIREMENTS.md:166` "by category and by priority" | The requirement |
| 2 | `AD-024`'s justification is false under the requirement | `OPEN-DECISIONS.md:334` "because the stats response includes counts by status" | `FUNCTIONAL-REQUIREMENTS.md:166` (no status counts) | Resolves with #1 |
| 3 | Frontend cannot cover the status counts it must render | `FUNCTIONAL-REQUIREMENTS.md:77` "Every category and priority enum value the server returns is rendered" | `AD-025` adds status counts | The requirement |
| 4 | `page_size > 100` — reject or clamp | `FR-BE-003`, `FUNCTIONAL-REQUIREMENTS.md:158` "either rejected with 400 **or** clamped to 100" | `AD-015`, `OPEN-DECISIONS.md:325` "**rejected with 400**" | The requirement |
| 5 | Limiter counter name | `BR-CACHE-007`, `BUSINESS-RULES.md:229` `rate_limiter_unavailable_total` | `AD-008`, `OPEN-DECISIONS.md:313` `rate_limiter_unavailable` | Either, consistently |
| 6 | `reporter_contact` privacy strength | `NON-FUNCTIONAL-REQUIREMENTS.md:158` "**SHOULD.**" | `BUSINESS-RULES.md:193` and `AD-003` — absolute | The NFR; this is a `MUST` |
| 7 | Build-time SHA vs build-once-deploy-many | `AD-034` derived, `OPEN-DECISIONS.md:369` "passed as a Docker build argument … legitimately *is* baked in" | `NON-FUNCTIONAL-REQUIREMENTS.md:210` "never at build time"; `FUNCTIONAL-REQUIREMENTS.md:100` "The same image digest serves the Compose stack and the Kubernetes cluster" | Needs an explicit carve-out |
| 8 | The load test never exercises the limiter it measures | `AD-017`, `OPEN-DECISIONS.md:327` "drives `GET /api/complaints` and `GET /api/stats`, which are not rate-limited" | `NFR-SCALE-001`, `NON-FUNCTIONAL-REQUIREMENTS.md:187` "Load test at ≥ 4 replicas with the rate-limit assertion still holding" | The measure |
| 9 | `AD-017` contradicts its own derived constraint | `OPEN-DECISIONS.md:327` names stats as a load target | `OPEN-DECISIONS.md:366` "The stats endpoint is cached, so the script must mix in uncached list queries" | The decision row |
| 10 | Seed supplies ids that must be server-generated | `AD-022`, `OPEN-DECISIONS.md:332` "deterministic UUIDv5 … with `ON CONFLICT (id) DO NOTHING`" | `AD-021`, `:331` "`id` default is **`gen_random_uuid()`**"; `FR-DATA-002:300` "**server-generated**"; `BR-VAL-006`, `BUSINESS-RULES.md:73` "A client-supplied id is never honoured" | Add an explicit seed exemption to `BR-VAL-006` |
| 11 | Seed must write statuses the invariant forbids | `FR-DATA-004`, `FUNCTIONAL-REQUIREMENTS.md:321` "a mix of statuses" | `BR-STATUS-001`, `BUSINESS-RULES.md:85` "Every complaint is created with status `open`. No other initial status is possible" | Scope `BR-STATUS-001` to the API path |
| 12 | Seed issues SQL from outside `repositories/` | `BR-DATA-003`, `BUSINESS-RULES.md:245` "No route, service, provider, script or test helper issues SQL from anywhere else" | `BUSINESS-RULES.md:250` "**Enforced at:** Seed command" | Exempt the seed and Alembic explicitly |
| 13 | UUIDv5 namespace is a placeholder | `docs/design/04-M3-data.md:70` "`uuid5(NAMESPACE, complaint_text)`" | `AD-022` claims "provably unchanged on a second run" | Fix the namespace to a literal |
| 14 | Image size budget is both `MUST` and `SHOULD` | `FUNCTIONAL-REQUIREMENTS.md:431` "**MUST** … at or below roughly 60 MB" | `NON-FUNCTIONAL-REQUIREMENTS.md:68` "**SHOULD** … approximately 60 MB" | Pick one strength |
| 15 | `ADR-0001`'s interface is synchronous | `docs/adr/0001-provider-interface.md:22` "`triage(text, location) -> TriageResult`" | `docs/design/06-M5-ai-triage.md:39` "`async triage(text, location)`" | The ADR |
| 16 | `ADR-0001` omits redaction from the pipeline | `docs/adr/0001-provider-interface.md:34` (cache → call → retry → validate → fallback) | `AD-003` and `06-M5-ai-triage.md:48` make redaction step 1 | The ADR |
| 17 | `ADR-0004`'s mitigation is in the cut order | `docs/adr/0004-pii-and-data-governance.md:66` "Switching to the zero-egress path is an environment variable, so the mitigation … already exists" | `AD-012`, `OPEN-DECISIONS.md:317` cuts `OllamaTriage` fourth | See the deviation register |
| 18 | Cut order disagrees with itself | `docs/design/09-M8-cicd.md:69` `release.yml` is "the first item in the declared cut order" | `OPEN-DECISIONS.md:317` "(1) VPA loop, (2) `release.yml`" | The design doc |
| 19 | Ollama cannot pull weights on a no-egress network | `docs/design/06-M5-ai-triage.md:79` and `07-M6-containers.md:60` — "pulled once … as a documented setup step" | `AD-002` puts Ollama on `internal` only; `OPEN-DECISIONS.md:367` still asks "must happen on a network that permits it, **or** be a documented one-time setup step" | An unresolved sub-decision inside a RESOLVED row |
| 20 | Network segmentation does not hold on Kubernetes | `docs/design/07-M6-containers.md:113` "`BR-SEC-001` — frontend cannot reach the database \| −8" | `docs/design/08-M7-kubernetes.md:22` — no `NetworkPolicy` in the object list | Add a NetworkPolicy or state the limitation |
| 21 | Healthchecks on every service, or only the backend | `docs/design/07-M6-containers.md:88` "Healthchecks on every service" | `docs/design/08-M7-kubernetes.md:50` — probes for the backend only | The Kubernetes doc |
| 22 | `PATCH` with a bad target on an unknown id | `docs/design/01-api-contract.md:127` "400 \| Target is not a valid status value" | `docs/design/01-api-contract.md:257` "PATCH on an unknown id with an invalid target → **404**, not 409" | State the precedence order |
| 23 | Metric label violates the document's own cardinality rule | `docs/design/00-conventions.md:180` `triage_fallback_total` labelled by `error_class` | `docs/design/00-conventions.md:186` "the raw path would create one time series per complaint id and blow up the metric cardinality" | Bound `error_class` to a closed set |
| 24 | The env registry claims completeness and is not | `docs/design/00-conventions.md:83` "No module reads `os.environ` directly"; `03-M2-backend.md:146` "typed settings for every variable in `00-conventions.md` §3" | Missing: `IMAGE_TAG` (`07-M6-containers.md:96`), the Postgres credentials (`:89`), the trusted-proxy config (`05-M4-cache.md:52`), the backend listen port, `PROMPT_VERSION` (`AD-019`) | The registry |
| 25 | Backend port is pinned only in an ADR parenthetical | `docs/adr/0002-frontend-runtime-config.md:12` "`backend:8000`" | No design doc or env var fixes it | Add it to the registry |
| 26 | Triage-cache ownership is split three ways | `BUSINESS-RULES.md:176` "SVC/PROV cache layer" | `MODULE-MAP.md:80` (M4.3), `:92` (M5.6), `RUBRIC-TRACEABILITY.md:74` "M4.3, M5" | Name one owning module |
| 27 | Cache-hit `triaged_by` nuance is impossible | `docs/design/05-M4-cache.md:69` "A hit yields `triaged_by` of the original provider (not `rules`)" | `:60` — the key already contains the provider name, so a hit can only come from the current provider | Delete the nuance |
| 28 | CORS is required and made unexercisable | `FR-BE-012`, `FUNCTIONAL-REQUIREMENTS.md:200` "**MUST.** Cross-origin requests from the frontend origin succeed in every deployment topology" | `AD-001`, `OPEN-DECISIONS.md:306` "No CORS in the browser's view (same origin)"; `:368` limits CORS to dev and integration tests, whose origins are unspecified | The requirement |
| 29 | CORS middleware ordering | `docs/design/03-M2-backend.md:59` — CORS is innermost, after logging and metrics | 4xx from outer middleware carries no CORS headers; preflight `OPTIONS` status codes are never specified | The middleware order |
| 30 | `localhost` prohibition has three different scopes | `FR-FE-016`, `FUNCTIONAL-REQUIREMENTS.md:109` "for reaching the backend in any containerised environment" | `NFR-PORT-005:226` "in any committed configuration"; `BR-SEC-004:280` "as a service-to-service address" | Unify them; see the note below |
| 31 | `.env` is required in the tree and forbidden in the tree | `FR-CTR-010`, `FUNCTIONAL-REQUIREMENTS.md:467` "All credentials come from `${...}` substitution backed by `.env`" | `NON-FUNCTIONAL-REQUIREMENTS.md:117` "No credential, key or token exists in the working tree" | Scope the NFR to tracked files |
| 32 | Frontend's stated worst case understates the contract | `FUNCTIONAL-REQUIREMENTS.md:34` "including a request that takes 10 seconds" | `:388`+`:392` and `AD-004` — 10 s timeout **plus** one jittered retry, so ≥ 20 s | The frontend requirement |
| 33 | Triage cache key defined two ways | `FR-CACHE-004`, `FUNCTIONAL-REQUIREMENTS.md:348` "a hash of the normalised complaint content" | `AD-019`, `OPEN-DECISIONS.md:329` — SHA-256 of redacted text + location + provider + prompt version | The requirement |
| 34 | `char_length` check vs trimming | `docs/design/04-M3-data.md:27` `CHECK (char_length(text) BETWEEN 10 AND 2000)` | `docs/design/01-api-contract.md:53` "10–2000 characters **after trimming**" — never states the trimmed value is what persists | State it |
| 35 | Required checks — one or several | `NON-FUNCTIONAL-REQUIREMENTS.md:255` "Both are required checks on `main`" | `FUNCTIONAL-REQUIREMENTS.md:599` "CI required as a status check" (singular); `docs/design/09-M8-cicd.md:22` never enumerates which jobs | Enumerate them |
| 36 | `NFR-REL-003` is a `MUST` measured only by a bonus | `NON-FUNCTIONAL-REQUIREMENTS.md:85` "**Measure:** Demonstrated under load during a rolling update with zero failed requests (FR-LOAD-004)" | `FR-LOAD-004:623` is "bonus, +4", **SHOULD**, and `AD-012` puts bonuses out of scope | See the deviation register |
| 37 | `FUNCTIONAL-REQUIREMENTS.md` states a source-of-truth scope it exceeds | `:4` "Source of truth: … (§2, §3, §4)" | `:110`, `:440`, `:446`, `:468`, `:478`, `:645` all derive from §5.2 and §5.3 | The scope line |
| 38 | Engineering-notes scope excludes six required contents | `FR-DOC-004`, `FUNCTIONAL-REQUIREMENTS.md:645` "answers all eight §5.2 questions" | `:316`, `:353`, `:431`, `:436`, `:455`, `:459` each demand more in the same file (index justifications, the Redis-volume answer, image sizes, context sizes, volume justifications, the bind-mount rationale), as does `AD-030`'s namespace correction | `FR-DOC-004` |

**Note on #30.** `civic-station.localhost` (`AD-029`) does **not** violate these rules —
`NFR-PORT-005:226` and `BR-SEC-004:280` both scope the ban to service-to-service
addressing, and an Ingress host is not that. The defect is that `FR-FE-016:111` names
"repository grep in `scripts/check_submission.py`" as the verification method without
specifying a pattern, so a naive grep would fail on a legal string. Specify the pattern,
not just the tool.

---

## S3 — Unfalsifiable requirements

68 entries. The fix has one of three shapes, so they are grouped by shape rather than
listed one by one.

### Supply a number (31)

| Missing value | Where |
|---|---|
| Worst-case triage latency bound (stated as bounded, never as a number) | `NON-FUNCTIONAL-REQUIREMENTS.md:44` |
| "within the triage bound plus persistence time under normal conditions" — no percentile, no load level, "normal" undefined | `NON-FUNCTIONAL-REQUIREMENTS.md:48` |
| Cache TTL "30 seconds exactly" — no tolerance, no measurement method | `NON-FUNCTIONAL-REQUIREMENTS.md:52` |
| Triage cache hit-rate target | `NON-FUNCTIONAL-REQUIREMENTS.md:56` |
| Rollback "roughly thirty seconds" — no start or stop instant | `NON-FUNCTIONAL-REQUIREMENTS.md:279` |
| Restart-count observation window | `NON-FUNCTIONAL-REQUIREMENTS.md:89` |
| Secret-shaped grep patterns (the pattern set is never defined) | `NON-FUNCTIONAL-REQUIREMENTS.md:142` |
| Image size budget — "expected", "roughly", and no measurement basis | `FUNCTIONAL-REQUIREMENTS.md:431`, `NON-FUNCTIONAL-REQUIREMENTS.md:68`, `07-M6-containers.md:36,149` |
| Build-context size threshold (numbers reported, nothing can fail) | `FUNCTIONAL-REQUIREMENTS.md:435` |
| `startupProbe` `failureThreshold` and `periodSeconds` (the brief gives 30 and 2 at `Problem_Statement.md:283`) | `FUNCTIONAL-REQUIREMENTS.md:510`, `BUSINESS-RULES.md:321` |
| `preStop` duration — "long enough" | `FUNCTIONAL-REQUIREMENTS.md:532`; `08-M7-kubernetes.md:105` says "sleep ~5s" |
| `terminationGracePeriodSeconds` | `FUNCTIONAL-REQUIREMENTS.md:248` |
| Retry jitter base, range and upper bound | `FUNCTIONAL-REQUIREMENTS.md:392`, `06-M5-ai-triage.md:60` |
| Rate limit value (exists only in `AD-017`, in no requirement) | `FUNCTIONAL-REQUIREMENTS.md:343`, `BUSINESS-RULES.md:161,219` |
| `Retry-After` value and format (delta-seconds or HTTP-date) | `BUSINESS-RULES.md:219` |
| Readiness check timeout — "a short timeout (≈ 1 s)" | `01-api-contract.md:208` |
| Dashboard page size — "fixed at a value ≤ 100" | `02-M1-frontend.md:64` |
| `RuleBasedTriage` confidence — "a fixed modest value" | `06-M5-ai-triage.md:92` |
| The low-priority keyword set (the high set is enumerated) | `06-M5-ai-triage.md:91` |
| `triaged_by` `CHECK` value set (a literal ellipsis) | `04-M3-data.md:34` |
| `triage_confidence` `CHECK` expression (no column operand) | `04-M3-data.md:35` |
| Redis `maxmemory` and eviction policy — four workloads share database 0 | `05-M4-cache.md:90`, `00-conventions.md:88` |
| Load profile: VUs, stage durations, request mix, `thresholds` | `10-M9-load-evidence.md:27`, `FUNCTIONAL-REQUIREMENTS.md:612,616` |
| Failed-request denominator for "show zero failed requests" | `FUNCTIONAL-REQUIREMENTS.md:624` |
| Target replica count and scale-out time bound | `10-M9-load-evidence.md:103` |
| Per-status seed counts — "a mix of statuses" | `FUNCTIONAL-REQUIREMENTS.md:321`, `04-M3-data.md:68` |
| Seed realism criteria — "realistic", "Urdu-influenced" | `FUNCTIONAL-REQUIREMENTS.md:321` |
| Resource requests and limits for every container | see S1-6 |
| Overall per-request budget for `POST /api/complaints` | `06-M5-ai-triage.md:51`; `02-M1-frontend.md:39` specifies a client with no timeout or abort |
| Metric names, units, label sets, histogram buckets | `FUNCTIONAL-REQUIREMENTS.md:186`, `06-M5-ai-triage.md:69` |
| Log field names and timestamp format | `FUNCTIONAL-REQUIREMENTS.md:260` |

### Supply a data source (9)

| Metric | Stated source | Why it does not work |
|---|---|---|
| Triage cache hit rate | `FUNCTIONAL-REQUIREMENTS.md:349`, "counter-derived ratio" at `NON-FUNCTIONAL-REQUIREMENTS.md:57` | No cache hit/miss counter exists in `FR-BE-009:186`'s metric set |
| HPA lag in seconds | `NON-FUNCTIONAL-REQUIREMENTS.md:199` "backed by the `hpa -w` capture" | `kubectl get hpa -w` emits no timestamps |
| Replicas vs offered load over time | `AD-044`, `OPEN-DECISIONS.md:359` "the k6 summary" | A summary is an aggregate, not a time series |
| Per-provider latency | `FUNCTIONAL-REQUIREMENTS.md:419` | No sample size and no statistic named; two candidate sources (the 20-entry ring buffer, `triage_latency_ms`) and no choice |
| Aggregate limiter behaviour at ≥ 4 replicas | `NON-FUNCTIONAL-REQUIREMENTS.md:187` | The resolved load test avoids rate-limited endpoints (S2-8) |
| Rollback duration | `NON-FUNCTIONAL-REQUIREMENTS.md:280` "Timed demonstration on video" | No start or stop event, no tool, no recorded location |
| "One inference, eight cache hits" scenario | `NON-FUNCTIONAL-REQUIREMENTS.md:322` | No counter to read it from |
| `/metrics` consumers | `01-api-contract.md:239` | No Prometheus is deployed; scraping is a +2 bonus |
| Provider live rate limits | `AD-006`, `OPEN-DECISIONS.md:311` | An open action item with no owner and no landing requirement |

### Supply an acceptance predicate (28)

Whole requirement families are verified by "review" with no assertable observable:

- `FR-K8S-001`–`014` — only `FR-K8S-006:511` states an acceptance criterion; the rest are "Manifest review" (`FUNCTIONAL-REQUIREMENTS.md:485–547`).
- `FR-CICD-001`–`013` — every entry is "Workflow review" or "Pipeline run"; `FR-CICD-001:555` covers a seven-job requirement with no assertion (`:553–605`).
- `FR-DOC-001`–`008` — "Review" for six of eight; `FR-DOC-006:654` is "Directory review", which does not check that captures show what they claim (`:632–662`).
- `FR-PROC-001`–`005` — "Git history", "Repository review", "Evidence"; `FR-PROC-005:684` ("Each partner can explain, and modify live, any part of the submission") is unverifiable in principle.
- `FR-CTR-001`, `002`, `004`, `006`–`011` — "review" or "captured numbers" with no pass/fail predicate (`:426–479`).
- `FR-FE-017`, `018`, `019` (`:115`, `:119`, `:124`) — no **Acceptance** clause at all.
- `FR-BE-011:195` — the grep is the whole test and will not catch an indirect session acquisition; no behavioural criterion.
- `FR-BE-016`, `019`, `020`, `025`, `026` — "Verify: Code review" as the sole method.
- `FR-DATA-005:325` — persistence across restarts, "Manual … CI where feasible", no row count or known-id check in the requirement.
- `FR-CACHE-005:352` — AOF plus a written justification, no test and no standard for the justification.
- `FR-CACHE-006:356` — "Verify: Test, ADR or engineering notes"; the behaviour under test is only in a Note, so the test has no specification.

Recurring escape hatches worth naming: "CI where feasible" (`:327`, `:447`) makes the
verification method optional; `Manual` is defined as "a demonstrable command **or**
screenshot" (`:11`), so a `MUST` may have no reproducible command; and "meaningful"
component tests (`:131`), "visibly different" UI states (`:46`), "small enough to read in
a PR" (`NON-FUNCTIONAL-REQUIREMENTS.md:267`) and "Generic answers score zero" (`:645`) are
review judgements presented as criteria.

### Undecided design points presented as design

Distinct from the above: places where an option list stands in for a decision.

| Point | Citation |
|---|---|
| JSON mode or a response schema | `06-M5-ai-triage.md:69` |
| Init container or pre-rollout Job for migrations — "either is defensible if the choice is stated" | `08-M7-kubernetes.md:43` |
| Fixed-window or token-bucket limiter (different burst semantics, so the 429 boundary is untestable) | `FUNCTIONAL-REQUIREMENTS.md:343` |
| Kustomize, or Helm "permitted instead, with an ADR" inside a `MUST` | `FUNCTIONAL-REQUIREMENTS.md:537` |
| SHA tag "(or digest)" — two acceptance targets for the checker script | `FUNCTIONAL-REQUIREMENTS.md:541` |
| Generated **or** mechanically-checked types (the stated acceptance only holds for "generated") | `FUNCTIONAL-REQUIREMENTS.md:88` |
| k6 "or an equivalent `hey` invocation" — `hey` cannot express a ramp | `FUNCTIONAL-REQUIREMENTS.md:612` |
| Import-graph **or** grep static check, neither specified | `NON-FUNCTIONAL-REQUIREMENTS.md:17` |
| Extra request fields "ignored or rejected, consistently, and the choice is documented" — no `AD` resolves it | `BUSINESS-RULES.md:69` |
| Enforcement point "DB (server-side default) **or** SVC" | `BUSINESS-RULES.md:74` |
| `triaged_by` column type "text/enum" inside a normative schema table | `FUNCTIONAL-REQUIREMENTS.md:308` |
| A second migration revision "may add indexes if the first is already merged", while `T-M3-004` assumes 0002 exists | `04-M3-data.md:59` |
| Redis-volume justification deferred to the implementer — "a different answer is fine if it is argued" | `05-M4-cache.md:92` |
| nginx non-root writable temp paths, user and listen port — "configure them explicitly", none given | `07-M6-containers.md:34` |
| Dev and prod overlay values | `08-M7-kubernetes.md:130` |
| `BACKEND_ORIGIN` format and example (every other URL var has one) | `00-conventions.md:106` |
| Which decisions after the first four get an ADR | `11-M10-documentation.md:46` |

### Missing operational specifics

- **Cache stampede.** `05-M4-cache.md:31` — concurrent misses, and every miss right after an invalidating write, all run the aggregation. No lock, no single-flight, no stale-while-revalidate.
- **Trusted proxy.** `05-M4-cache.md:52` — "a trusted-proxy configuration" with no trusted list, no env var and no rule for which `X-Forwarded-For` entry is authoritative, so the per-IP limiter is spoofable by a client setting the header. This is the brief's "keyed by client IP" (`Problem_Statement.md:136`) made unimplementable by `AD-001`'s proxy and the Ingress.
- **Outcomes ring buffer.** `05-M4-cache.md:19` — `cs:outcomes`, TTL "none", no invalidation, so entries survive a provider or prompt change with nothing tying them to `PROMPT_VERSION`.
- **Kubernetes hardening.** `08-M7-kubernetes.md:22` — no `securityContext`, `runAsNonRoot`, `readOnlyRootFilesystem`, `NetworkPolicy`, `ResourceQuota` or `LimitRange`; no image tags for `postgres` or `redis` in the manifests, though `09-M8-cicd.md:141` gates on "every manifest image has an explicit tag".
- **Secret rotation.** `08-M7-kubernetes.md:121` — no rotation procedure and no statement of what happens to running pods (see S1-11).
- **No rollback in the pipeline.** `09-M8-cicd.md:56` — the deploy job has no failure path, no automatic `rollout undo` and no gate on the smoke test's result. Rollback exists only as a manual demo (`08-M7-kubernetes.md:176`).
- **`check_submission.py` is never wired into CI.** `09-M8-cicd.md:126` defines it; the job table at `:30` omits it, so the §5.3 deduction guards run only when a human remembers.
- **No frontend coverage gate.** `09-M8-cicd.md:33` gates backend coverage at 65 %; the frontend has only "≥ 5 component tests" as prose.
- **Expand/contract not required.** `04-M3-data.md:57` — migrations run from an init container (`08-M7-kubernetes.md:41`) while `maxUnavailable: 0` (`:102`) keeps old pods serving against the new schema, with no compatibility rule stated.
- **SBOM has no destination.** `FR-CICD-009:586` requires emitting one; no document says where it is stored, attached or retained.
- **`/docs` exposure in production** is never decided; it is specified in prose at `01-api-contract.md:220` and absent from the endpoint summary table and every contract test.

---

## S4 — Traceability

1. **32 business rules that nothing references.** Defined once each, cited by no requirement, ADR or rubric row: `BR-VOCAB-002/003/005`, `BR-VAL-002/003/005/006/007`, `BR-STATUS-001/003/006/007`, `BR-TRIAGE-002/004/008/009/012/014`, `BR-CACHE-001/005/006`, `BR-DATA-002/005`, `BR-SEC-002/004/005`, `BR-DEL-002/004`, `BR-OPS-002/003/004/005`.
2. **34 NFRs that nothing references**, including all four `NFR-MAINT-*` (`NON-FUNCTIONAL-REQUIREMENTS.md:254–267`) and all four `NFR-OBS-*` (`:165–177`).
3. **12 `MUST`s absent from `RUBRIC-TRACEABILITY.md`**, contradicting `:8` "Use it in two directions". Notably `FR-DATA-005:325` (persistence across restarts), which the brief demands a demo of at `Problem_Statement.md:128`. Also `FR-CACHE-006`, `FR-CICD-005`, `FR-CICD-010` (`release.yml`), `FR-K8S-010` (PDB), `FR-K8S-012` (Kustomize), `FR-K8S-014` (rollback), `FR-LOAD-001`, `FR-DOC-005/006/007`, `FR-PROC-005`.
4. **The whole M1.4/M1.6 block is unmarked.** `FR-FE-012`, `013`, `015`, `016`, `017`, `018`, `019` (`FUNCTIONAL-REQUIREMENTS.md:87–126`) appear in no section-B rubric row.
5. **Nine `FR-BE-*` `MUST`s unmarked**: `012`, `013`, `015`, `017`, `018`, `019`, `020`, `025`, `026`.
6. **Range notation defeats traceability.** `FR-BE-001…010`, `FR-FE-001…005`, `FR-AI-006…008` and others (`RUBRIC-TRACEABILITY.md:31,32,41,73,94,105`) hide which IDs are actually covered, while `:157` asks a human to "walk every row".
7. **Malformed identifier.** `RUBRIC-TRACEABILITY.md:44` cites `BR-OPS/NFR-REL-004`; `BR-OPS` is not an ID under `MODULE-MAP.md:191`'s convention.
8. **Two marked bonus rows have no requirement.** `RUB-X-05:131` (OpenTelemetry, +2) maps to nothing; `RUB-X-04:130` maps only to `FR-BE-009`, leaving the Grafana dashboard requirement-less.
9. **Declared-and-unused conventions.** `T-<MOD>-nnn` and `RUB-<X>-nn` (`MODULE-MAP.md:194,196`) — no `T-` identifier appears in any of the five requirement docs or the decision log, and all 40 `RUB` IDs occur exactly once (their own definition). Requirements cite the rubric in prose instead ("Rationale: Rubric C, 4 marks", `FUNCTIONAL-REQUIREMENTS.md:254`), so traceability runs one way only.
10. **Sub-module IDs defined and unreferenced.** `FUNCTIONAL-REQUIREMENTS.md:17–133` uses `## M1.1`–`## M2.7` headings; M3–M11 requirements carry none, though `MODULE-MAP.md:5` says requirement IDs "key off the identifiers on this page".
11. **`M5`'s dependency invariant is indeterminate.** `MODULE-MAP.md:181` says "M5 never depends on M2.2 or M2.3" and is silent on M4, which `FR-AI-012` and `FR-CACHE-004` both require.
12. **A self-cancelling exception.** `NON-FUNCTIONAL-REQUIREMENTS.md:36` — "Exception: none. `AD-009` places the triage outcome ring buffer … in a Redis list, so even that state is shared" — states "none" and then the exception.
13. **`docs/README.md` contains zero markdown links.** A search for `[text](target)` in that file returns nothing, though `:13` calls the file "the map". The index is a fenced tree with three files per line (`:35–38`), so nothing is clickable or checkable.
14. **`docs/README.md` indexes a directory that does not exist.** `:45` lists `evidence/`; `docs/evidence/` is absent, and `02-weekly-plan.md:49`, `03-collaboration-protocol.md:93` and `README.md:86` all write into it.
15. **Four required deliverables are neither indexed nor present.** `Problem_Statement.md:586` places `ENGINEERING-NOTES.md`, `RUNBOOK.md`, `AI-USAGE.md` and `TRIAGE.md` under `docs/`; none is in the README tree or on disk.
16. **Four indexed documents are absent from the reading order.** `docs/README.md:50` omits `requirements/NON-FUNCTIONAL-REQUIREMENTS.md`, `requirements/RUBRIC-TRACEABILITY.md`, `schedule/01-work-breakdown-and-critical-path.md` and `schedule/03-collaboration-protocol.md`.
17. **No document has a named owner.** `docs/README.md:79` sets edit rules but names no owner of record for any file, unlike `03-collaboration-protocol.md:73`, which does have an owner column for shared code files.
18. **The root `README.md` is conflated with the docs index.** `docs/README.md:13` says "you are here: the map"; the repository-root `README.md` is a different 15-byte file, and it is a 4-mark deliverable (`Problem_Statement.md:476`).
19. **Milestone IDs are double-booked.** `MODULE-MAP.md:25` defines M1–M11 as *modules* (M1 = Frontend, M2 = Backend); `docs/schedule/01-work-breakdown-and-critical-path.md:233` reuses M0–M8 as *schedule milestones* (M1 = "Stack runs in Compose", M2 = "Backend feature-complete"); `03-collaboration-protocol.md:16` uses the module sense. Every bare "M4" in the doc set is ambiguous. This one outlives the schedule being discarded, because the module IDs are load-bearing in the requirements and design docs.

---

## Deviation register

Six places where the docs knowingly depart from the brief. These are decisions to make,
not defects to fix. Mark exposure is given so the trade is visible.

### D1 · Three networks instead of two — 4 marks

| | |
|---|---|
| **Docs** | `AD-002` (`OPEN-DECISIONS.md:307`), `07-M6-containers.md:53` |
| **Brief** | `Problem_Statement.md:222` — "**Networks — two, not one.**" |
| **Exposure** | `RUB-G-03` (`RUBRIC-TRACEABILITY.md:85`), 4 marks, text reads "Two networks with `internal: true`" |
| **For the deviation** | `internal: true` blocks egress, so a backend calling Groq needs a network that permits it. `07-M6-containers.md:58`: putting egress on `edge` would work but "makes the outbound capability an accidental side effect of the browser-facing network". Costs about six lines and turns engineering-notes Q7 into a design decision rather than an excuse. |
| **Against** | The brief poses Q7 (`:514`) *as* a question to be answered, and `:243` explicitly invites the student to "work out where that leaves your architecture" — so a two-network answer with the reasoning written down may be what the marker expects. A third network also makes the frontend-cannot-reach-database demo no more convincing than two do. |

### D2 · `GET /api/version` as an eleventh endpoint — 7 marks

| | |
|---|---|
| **Docs** | `AD-014` (`OPEN-DECISIONS.md:324`) |
| **Brief** | Nine endpoints at `:83–93`; the rubric says "All **ten** endpoints" at `:415` |
| **Exposure** | `RUB-C-01`, 7 marks |
| **State of play** | `FUNCTIONAL-REQUIREMENTS.md:192` makes `/openapi.json` the tenth, which is a reasonable reading of an under-specified rubric line. `AD-014` then adds `/api/version` as an eleventh, with no requirement defining it — so it ships outside the traced contract. `01-api-contract.md:229` lists 11 and `03-M2-backend.md:144` says "all 11 endpoints present", against the brief's "ten". |
| **Note** | `/api/version` also has no consumer: no view in `02-M1-frontend.md:29` reads it. Its cost is `AD-034`'s build-time SHA argument, which collides with build-once-deploy-many (S2-7). |

### D3 · Namespace `civic-station` — no exposure, docs are right

| | |
|---|---|
| **Docs** | `AD-030`, `08-M7-kubernetes.md:20` |
| **Brief** | `:268` "Everything in `Civic-Station`", `:384` `-n Civic-Station` |
| **Verdict** | The docs are correct and the brief is wrong: Kubernetes object names must be RFC 1123 lower-case, so `Civic-Station` is rejected. `08-M7-kubernetes.md:20` already says so. |
| **Action** | None, except confirming the correction has a documented home — `AD-030` (`OPEN-DECISIONS.md:345`) says it goes in the engineering notes, but `FR-DOC-004:645` scopes that file to the eight §5.2 questions only (S2-38). |

### D4 · `OllamaTriage` fourth in the cut order — 7 marks plus an ADR's premise

| | |
|---|---|
| **Docs** | `AD-012` (`OPEN-DECISIONS.md:317`) — "(4) `OllamaTriage` — dropping to three providers, which still satisfies the rubric" |
| **Exposure** | The rubric line is satisfied (`RUB-F-01` asks for "≥ 3 working implementations", 5 marks). But `FR-AI-002:370` is a `MUST` for all four, and `FR-CTR-007:455` is a `MUST` for three named volumes including `ollama_models` — `RUB-G-04`, 2 marks. Cutting Ollama also deletes the mitigation `docs/adr/0004-pii-and-data-governance.md:66` relies on ("Switching to the zero-egress path is an environment variable, so the mitigation … already exists and is already tested"). |
| **Note** | The brief explicitly blesses the Ollama-only path (`:178`: "you lose no marks for it"), so the risk is asymmetric — dropping Ollama is worse than dropping Groq. |

### D5 · Zero-downtime rollout treated as a bonus — a `MUST` with no owner

| | |
|---|---|
| **Docs** | `10-M9-load-evidence.md:77` "(FR-LOAD-004, +4 bonus)"; the cut order lists it third |
| **Brief** | `:293` states it in the body of §3.3, not in the bonus list: "Demonstrate a zero-downtime rollout: run a load generator during a `kubectl set image`, and show zero failed requests." It *also* appears as a +4 bonus at `:486`. |
| **Exposure** | `NFR-REL-003:85` is a `MUST` whose only stated measure is the out-of-scope bonus. So a required demonstration has no committed owner. |
| **Note** | The brief contradicts itself here, listing the same work as a body requirement and a bonus. Worth raising rather than guessing. |

### D6 · `ADR-0001`'s synchronous interface

| | |
|---|---|
| **Docs** | `docs/adr/0001-provider-interface.md:22` `triage(text, location) -> TriageResult` |
| **Design** | `06-M5-ai-triage.md:39` `async triage(text, location)` |
| **Exposure** | `RUB-J-02`, 4 marks for four ADRs. On the fully async stack fixed by `AD-005` these are not the same contract, and the ADR is the committed artefact a marker reads. |

---

## Appendix A — schedule findings, recorded not actioned

The schedule documents will not be used, so these are recorded for completeness and not
carried into the body. One schedule finding *is* in the body — the milestone ID collision
(S4-19) — because the module IDs it collides with are load-bearing elsewhere.

1. **A-package durations sum to 18.5, not 19.0.** `01-work-breakdown-and-critical-path.md:46` declares "**Subtotal: 19.0 blocks**"; the 19 listed durations sum to 18.5. The P subtotal of 20.0 (`:80`) is correct. The 0.5 error propagates into `:169` and the 46.0 grand total at `:171`, which should be 45.5.
2. **No calendar dates exist.** `:16` "No calendar dates. Day 1 is whenever the team starts." No start, end or submission date appears in any schedule doc, and `Problem_Statement.md:540` says late submissions are not accepted.
3. **A "day" is defined twice.** `02-weekly-plan.md:7` makes it 10 hours (2.5 blocks); `01-...:13,14` makes it 2 blocks. The entire "Target day" column is computed on a rate the other document contradicts.
4. **Seven of nine milestone dates conflict between the two documents.** M1 Day 2 vs Day 3; M2 Day 3 PM vs no gate at all; M3 Day 4 AM vs end of Day 4; M4 Day 5 AM vs end of Day 5; M5 Day 5 PM vs Day 6; M6 Day 6 AM vs Day 7; M7 Day 6 PM vs Day 7.
5. **The day plan does not fit the day it defines.** Dev 1's Day 1 is 3.0 blocks and Day 3 is 4.0; summed across `02-weekly-plan.md`, Dev 1 carries ~24.5 blocks against the 15.5 that `01-...:207` computes after rebalancing.
6. **The rebalance does not close the gap.** `:207` "Both about 2 blocks over a 14-block week", and 0.5 blocks vanish in the transfer (subtracted raw from Dev 2, added compressed to Dev 1).
7. **The `P20` cut claim does not follow.** `:224` calls cutting `P20` "the single most schedule-effective cut available" because it "shortens the critical path by 1 block". Given the stated dependencies at `:77`, `P24` also depends on `P17` and `P21`, both finishing at 10.0, so removing `P20` changes nothing. Repeated uncorrected at `02-weekly-plan.md:91`.
8. **S1 and S2 have no predecessors.** `:88,89` put "mid-week" and "~two-thirds point" in a column headed "Depends on" — dates, not predecessors, so neither package is in the network the forward pass at `:101` claims to have run.
9. **The float table is incomplete and not reproducible.** `:135` lists 45 of 50 packages; `P3`, `P8`, `P25`, `S1` and `S2` have no float value, including `P8`, which carries Trivy and kubeconform (3 marks). Several listed values do not recompute from the stated network.
10. **Walkthrough durations differ 5×.** `:88` gives S1 0.5 blocks (4 h); `02-weekly-plan.md:83` and `03-collaboration-protocol.md:128` call it ~45 minutes.
11. **Five design tasks are in no work package.** `T-M4-010`, `T-M9-005`, `T-M10-001`, `T-M10-003`, `T-M11-003` appear in `docs/design/` and zero times in `docs/schedule/`, falsifying "132 tasks grouped into 50 work packages" (`docs/README.md:70`). They are defined, so they have a home; only the schedule misses them. `T-M9-005` feeds engineering-notes Q5, and `T-M10-003` (README quickstart verified from a clean clone) carries a −5 deduction.
12. **Q8 has no package and no owner.** `01-...:239` gates M7 on "Eight notes answered"; seven are assigned (`:77` P24 → Q1/Q2/Q6/Q7, `:90` S3 → Q3/Q4/Q5) and `03-collaboration-protocol.md:120` assigns Q8 to "Either". `ENGINEERING-NOTES.md` is never named in any schedule doc.

Also worth noting, since it undercuts every "Status: Authoritative (Round 4)" header:
**everything under `docs/` except `docs/planning/` is untracked in git.** Nothing the
README declares authoritative has been committed.

Collaboration-protocol gaps, recorded for the same reason: no tie-breaker if the
15-minute decision rule at `03-collaboration-protocol.md:156` expires; no merge-method
rule, though `Problem_Statement.md:401` needs a preserved merge commit and `:399` needs
≥ 35 commits, both of which squash-merge destroys; no unavailability procedure for the
sole reviewer; no communication channel named anywhere; no definition of done for a
milestone or a day gate; and no protocol for sharing the API key between machines. The
commit-count floor of 35 (`:399`) appears in no schedule doc — `:141` covers only the
35 % balance.

---

## Appendix B — method and confidence

**Read in full:** `docs/planning/Civic-Station_Problem_Statement.md` (611 lines) and all 27
other files under `docs/`.

**Verified by recomputation or direct read** (not taken on trust):

- The rubric sum, per section and in total, computed from `RUBRIC-TRACEABILITY.md`'s own rows. Result 175 + 15 bonus.
- The A- and P-package duration subtotals, same method. A = 18.5 against a declared 19.0; P = 20.0, correct.
- The `triaged_by` chain across `01-api-contract.md:37`, `04-M3-data.md:34`, `06-M5-ai-triage.md:99`, `09-M8-cicd.md:33` and `03-M2-backend.md:175`.
- The `ai_summary` contradiction, including that `AD-023` is a resolved row.
- The index-versus-query mismatch, by reading the filter and order rules and both index definitions.
- The `OPEN-DECISIONS.md` open/closed contradiction and the `Round 2` date placeholders in all four ADRs.
- The two-versus-three-networks chain, including that `RUB-G-03` cites both conflicting sources.
- The milestone ID collision, by reading both definition tables.
- `AD-021`/`AD-022` and `BR-VAL-006`, for the seed identity contradiction.
- The absence on disk of `backend/`, `frontend/`, `k8s/`, `load/`, `compose.yaml`, `compose.prod.yaml`, `.env.example`, `scripts/check_submission.py`, `docs/ENGINEERING-NOTES.md`, `docs/RUNBOOK.md`, `docs/AI-USAGE.md`, `docs/TRIAGE.md` and `docs/evidence/`.
- The five orphan design tasks, by counting occurrences in `docs/design/` versus `docs/schedule/`.
- Credential rotation and API-key acquisition, by searching `docs/requirements/`, `docs/design/` and `docs/adr/` for any coverage. None found.

**Two claims were investigated and dropped or downgraded**, recorded so they are not
re-raised:

1. *"`civic-station.localhost` violates the `localhost` prohibition."* It does not.
   `NFR-PORT-005:226` and `BR-SEC-004:280` both scope the ban to service-to-service
   addressing; an Ingress host is not that. What remains is the unspecified grep pattern
   (S2-30).
2. *"`/health`, `/ready`, `/metrics`, `/openapi.json` and `/docs` are unroutable."* They
   are not broken. `08-M7-kubernetes.md:144` says the CI smoke test exercises the Ingress
   `/api` path; Kubernetes probes address pods directly, not through the Ingress; and
   `/openapi.json` is consumed at build time by `T-M1-003`
   (`02-M1-frontend.md:119`), not by the browser. What remains is that no document states
   this deliberately, and `/docs` exposure in production is never decided — recorded under
   S3 rather than as a blocker.

**Reported at lower confidence**, i.e. read once and not independently re-derived: the
individual entries inside the S3 tables and the S4 unreferenced-ID counts. The counts were
produced by enumeration over the files; spot-checks matched, but a full re-derivation of
all 66 unreferenced `BR`/`NFR` identifiers was not performed. Treat the counts as accurate
to within a small margin and the individual citations as reliable.

**Not audited:** any code, since none exists; the brief's own internal consistency beyond
where the docs inherit a defect from it (the 150-versus-175 total, the two-versus-four-week
duration, the ten-versus-nine endpoints, and the zero-downtime requirement-versus-bonus
are all brief-level defects, flagged where they land).
