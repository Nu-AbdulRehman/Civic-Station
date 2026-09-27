# Failure log

One entry per thing that cost real time: the symptom, what was wrongly believed first, and the
command or line that told the truth (`CLAUDE.md` §5, feeds engineering-notes Q8).

This file was created on 2026-09-26 during work package A13. The entries below are from earlier
the same day (A3–A10) and are recorded from the commands and outputs of that session, not
reconstructed from memory; from here on, entries are appended as the failure happens.

---

### 2026-09-26 · A3 · A deleted `DROP TYPE` did not fail the migration test
- **Symptom:** removing the enum-type drops from revision `0001`'s `downgrade` left the up → down → up test green.
- **Wrongly believed:** the up/down/up cycle proves the downgrade is complete.
- **Truth:** SQLAlchemy's PostgreSQL `ENUM.create()` defaults to `checkfirst=True`, so the next upgrade silently reused the leftover type. Fixed by `checkfirst=False` on create and drop, plus an assertion that no `complaint_*` enum type survives `downgrade base` (`backend/tests/integration/test_schema.py`).

### 2026-09-26 · A4 · Two concurrency/ordering tests could not fail
- **Symptom:** removing `with_for_update=True` and the `id DESC` tie-break both left the repository tests green.
- **Wrongly believed:** `asyncio.gather` of two status changes makes them overlap; a small table exposes a missing tie-break.
- **Truth:** the coroutines never interleaved at the database, and the planner returned index order anyway. Replaced with a test that holds the row lock from a second connection and waits on `pg_stat_activity` for a `Lock` wait, and a test that captures the emitted SQL and asserts the `ORDER BY`.

### 2026-09-26 · A5 · Single-flight test passed with the lock deleted
- **Symptom:** "20 concurrent cold readers run one aggregation" stayed green with the Redis lock removed.
- **Wrongly believed:** twenty tasks started together are twenty cold readers.
- **Truth:** the other callers' `GET` reached Redis after the winner had already cached the value. The test now holds the aggregation until a proxy has seen twenty empty reads; with the lock removed it fails with `assert 20 == 1`.

### 2026-09-26 · A9 · Mutation runner hung and left a mutated file in place
- **Symptom:** the "no timeout" mutation of `pipeline.py` hung the test run; the script's `subprocess.run(timeout=60)` never returned, and the working tree kept the mutation.
- **Wrongly believed:** a subprocess timeout kills the whole pytest tree on Windows.
- **Truth:** the killed `uv` left its Python child holding the pipes. Fixed by killing the process tree and restoring from the pre-mutation backup; later mutation runs restore the file in a `finally`.

### 2026-09-26 · A10 · Contact-leak mutation survived
- **Symptom:** passing `reporter_contact` into triage left the test green.
- **Wrongly believed:** asserting that an email address never reaches the provider tests the contact exclusion.
- **Truth:** `redact()` scrubbed the email first, masking the leak. The test now uses a plain name, which redaction cannot catch.

### 2026-09-26 · A15 · Three Submit error-state tests failed with the very error they injected
- **Symptom:** every `SubmitErrors` test failed with the `ApiError` it had passed to `mockRejectedValue`, although the page rendered the right state.
- **Wrongly believed:** vitest 5's `mockRejectedValue` creates its rejected promise eagerly and the runner reports it as unhandled; a workaround was written on that basis.
- **Truth:** `beforeEach(() => vi.mocked(fn).mockReset())` *returns* the mock, and vitest runs a function returned from `beforeEach` as teardown — so after each test it called the mock, which threw. Isolated by a debug test that passed without the `beforeEach`. Fixed with block-bodied hooks; the workaround and its wrong explanation were removed.

### 2026-09-26 · A19 follow-up · Live Groq smoke run fell back to rules on every call
- **Symptom:** with a valid key, `POST /api/complaints` returned 201 but `triaged_by: rules:fallback`, `error_class: Other`.
- **Wrongly believed:** the key was wrong (401), which would also classify as `Other`.
- **Truth:** a direct `LLMTriage` call surfaced `404 model_not_found` for the pinned `llama-3.1-8b-instant`; `GET /models` showed Groq no longer serves a Llama chat model. The resilience path did its job — the citizen got a 201 — but it also hid the cause behind `Other`. The model was replaced with `qwen/qwen3.8-27b` after measuring both live candidates (`AD-045` revised). Lesson: a pinned hosted model is a dependency that can disappear; the smoke run is what catches it.

### 2026-09-27 · P3 · Frontend image looked 26 MB locally but would fail the 60 MB CI gate
- **Symptom:** `docker image inspect -f '{{.Size}}'` printed 26 MB for the frontend image on the laptop, comfortably under the gate.
- **Wrongly believed:** that number is the unpacked size the CI gate measures.
- **Truth:** Docker Desktop here uses the containerd image store, where `.Size` is the *compressed* content size. `docker history` showed ~67 MB unpacked, driven by the full `nginx:alpine` variant's module layer; the CI runner's classic store reports that unpacked number. Switched to the `-slim` variant (~15 MB unpacked, `AD-063`). Measure with `docker history` layer sums, not `inspect`, on a containerd-store machine.

### 2026-09-27 · P3 · Pinned nginx 1.27 base failed the Trivy gate
- **Symptom:** Trivy with `--ignore-unfixed` found 40 HIGH/CRITICAL (openssl, c-ares, expat) in `nginx:1.27.5-alpine`.
- **Wrongly believed:** pinning the version the design doc names is enough for a clean scan.
- **Truth:** the 1.27 line sits on Alpine 3.21, which no longer receives rebuilds, so fixed CVEs accumulate. Pinning freezes vulnerabilities as well as behaviour; the pin has to be to a maintained line (`AD-063`).
