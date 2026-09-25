# ADR-0002 — Frontend runtime configuration

- **Status:** Accepted
- **Date:** 2026-09-16 (accepted). Revised 2026-09-25 by the specification audit.
- **Decides:** `AD-001`
- **Related requirements:** `FR-FE-014`, `FR-FE-016`, `FR-BE-012`, `FR-K8S-004`, `NFR-PORT-001`

## Context

Vite inlines `import.meta.env` values into the static JavaScript bundle at **build** time. If the backend URL is read that way, the compiled bundle contains a literal address and the resulting image only works in the environment it was built for.

That destroys build-once-deploy-many for the frontend. The same image must serve the Compose stack (backend reachable as `backend:8000` on the `edge` network) and the Kubernetes cluster (backend reachable through an Ingress on a different host), with no rebuild — and the CD pipeline deploys by commit SHA, so a rebuild per environment would mean the SHA no longer identifies one artefact.

A second, related problem: if the browser talks to the backend on a different origin, every deployment topology needs correct CORS configuration, and CORS misconfiguration is one of the most common and most time-consuming failures in exactly this kind of project.

## Decision

**nginx, in the frontend container, reverse-proxies `/api` to the backend. The frontend uses relative URLs only and never knows a backend address.**

- The API client issues requests to `/api/...`. There is no configurable base URL in the JavaScript at all — the problem is removed rather than solved.
- `nginx.conf` is a template. The proxy target comes from an environment variable (`BACKEND_ORIGIN`) substituted at container start by `envsubst` in the entrypoint, before nginx starts.
- On Kubernetes, the Ingress routes `/` to the frontend Service and `/api` to the backend Service on one host. The nginx proxy and the Ingress express the same routing at two layers; either path works, and the frontend behaves identically.
- The backend retains a CORS configuration driven by an environment variable, for direct-access cases: local development against the Vite dev server, and the integration tests.

## Alternatives considered

**`/config.js` generated at container start**, loaded before the application bundle, exposing `window.__CONFIG__.apiBaseUrl`. This is the other correct answer and is explicitly offered by the brief. Rejected because it keeps the browser talking cross-origin, which means CORS must be correct in every topology, and because the typed API client then has to read configuration at call time rather than being a static module — a small but real complication in every test.

**Bake the URL in with a per-environment build.** Rejected: this is the failure the requirement exists to prevent. It produces one image per environment, so "what is production running?" stops having a one-word answer.

**Both mechanisms** — proxy on Kubernetes, `/config.js` in Compose. Rejected: two mechanisms, two failure modes, and two things to explain at viva, in exchange for nothing.

## Consequences

**Good.**
- The exact line that guarantees build-once-deploy-many for the frontend is the `envsubst` substitution of `BACKEND_ORIGIN` in the entrypoint — a single, citable line, which is what engineering-notes question 3 asks for.
- The browser makes same-origin requests, so CORS is not a source of bugs in any deployed topology.
- The frontend cannot accidentally hard-code `localhost` for service-to-service traffic, because it has no backend address to hard-code. The −8 deduction in §5.3 becomes structurally impossible on the frontend side.
- One image digest demonstrably serves both environments, which is the demonstration `NFR-PORT-001` requires.

**Costs.**
- One extra network hop: browser → nginx → backend. Negligible at this scale, and it is the same hop the Ingress would make anyway.
- nginx is now a component with configuration that can be wrong, and that configuration is generated at runtime. The entrypoint must fail loudly if `BACKEND_ORIGIN` is unset rather than starting nginx with an empty proxy target.
- Requests are opaque to the browser's network tab in terms of which backend answered; the `X-Request-ID` echoed in responses (`FR-FE-013`) is how a reported failure is traced instead.

**Verification.** Build the frontend image once, record the digest, run it against the Compose backend and then against the Kubernetes Ingress with only the environment differing, and confirm both work. That demonstration is the evidence for rubric B-04.
