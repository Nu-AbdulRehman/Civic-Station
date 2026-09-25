# 10 — M9 Load testing and scaling evidence: design and implementation guide

**Owner:** Dev 2, with Dev 1 on the analysis write-ups
**Depends on:** M7 (HPA, VPA, resources), M2 (SIGTERM), M4 (limiter)
**Delivers:** `RUB-H-05` (HPA evidence) and `RUB-H-06` (the VPA loop), engineering-notes Q5 and Q6, and `RUB-X-01`. **`RUB-X-01` is no longer a bonus:** the brief states the zero-downtime rollout in the body of §3.3 at `:293`, not only as a bonus at `:486`, and `NFR-REL-003` is a `MUST` whose only measure is that demonstration — so `FR-LOAD-004` is required (`AD-012`). The manifests these rows are measured against are specified in `08-M7-kubernetes.md`.
**Stack:** k6 (`AD-043`), metrics-server, a committed plotting script (`AD-044`)

---

## 1. What this module is for

Proving that the scaling claims are true, and measuring the gap between what a manifest says and what a cluster does.

The learning outcome is not "the HPA worked". It is **noticing the lag** — the seconds between load arriving and capacity arriving — and being able to say where they went. That lag is the reason autoscaling is not a substitute for capacity planning.

---

## 2. The load script (`load/k6-script.js`)

**Targets `GET /api/complaints` and `GET /api/stats`** (`AD-017`), not the POST path. This keeps the rate limiter fully armed during the scaling demonstration, so there is nothing to explain away at viva — the alternative ("we disabled the limiter for the demo") is a worse answer even when it is honest.

**The script must actually create CPU load.** Two things work against this:

- `GET /api/stats` is cached with a 30-second TTL, so hammering it mostly exercises Redis, not the backend. Use it as a minority of traffic.
- `GET /api/complaints` with the *same* filters will be served from PostgreSQL's cache. **Vary the filters and the page number** across virtual users so queries are genuinely executed. This is the difference between a load test that scales the HPA and one that produces a flat CPU line and an afternoon of confusion.

**Stage profile (`AD-050`), as the actual options block** — previously this was four adjectives, which is not a load profile:

```js
export const options = {
  stages: [
    { duration: '60s',  target: 40 },  // ramp: makes the lag visible
    { duration: '180s', target: 40 },  // plateau above the 60% CPU target
    { duration: '30s',  target: 0 },   // ramp down
    { duration: '330s', target: 0 },   // idle > the 300s scale-down window
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
};
```

**Request mix per iteration:** 8 × `GET /api/complaints` with randomised `page`, `page_size` and filter combinations, 1 × `GET /api/stats`. A step function makes the lag measurable; a constant load does not.

**Acceptance, as numbers rather than a shape:** CPU utilisation exceeds 60 % during the plateau; replicas rise above 2; replicas return to 2 within 600 s of the idle stage beginning; both thresholds above hold, and the run fails if either is breached.

**Output: `--out json=docs/evidence/k6-timeseries.json`, not only the summary.** The summary is an aggregate — a single number per metric for the whole run — so it cannot supply the x-axis of a replicas-against-load-over-time chart. Recording the summary alone was the reason that chart had no data source (`AD-051`).

---

## 3. HPA scale-out capture (`FR-LOAD-002`)

Procedure:

1. `kubectl top nodes` returns data — if not, metrics-server is missing and nothing below works.
2. `kubectl get hpa -n civic-station` shows a real percentage. **If it shows `<unknown>/60%`, stop**: a `resources.requests.cpu` is missing, and the HPA has no denominator.
3. Start `kubectl get hpa -w -n civic-station | ts` (or equivalent timestamping) redirected to `docs/evidence/hpa-watch.txt`.
4. Run the k6 profile.
5. Stop the watch after the scale-down window has elapsed, so the capture shows the full curve in both directions.

**Deliverables:**
- `docs/evidence/hpa-watch.txt` — raw capture showing replicas rising.
- `docs/evidence/replicas-vs-load.png` — produced by `scripts/plot_scaling.py` from the capture plus the k6 summary (`AD-044`), so the chart is reproducible rather than a screenshot of a spreadsheet.
- 3–5 sentences on the lag (engineering-notes Q5).

**Where the lag actually goes** — the honest answer names each component, and the team should measure rather than recite:

| Component | Typical contribution |
|---|---|
| metrics-server scrape interval | ~15 s before new usage is even visible |
| HPA control-loop period | ~15 s between evaluations |
| Scheduling + image pull + container start | seconds to tens of seconds |
| **Startup probe + readiness** before the pod receives traffic | the startup probe's threshold is a floor here |

The last row is the one most teams miss: a pod counts as a replica before it is Ready, so the *capacity* arrives measurably later than the *replica count* rises. Comparing the HPA capture against the k6 latency curve shows this directly, and noticing it is the whole point.

---

## 4. VPA recommendation loop (`FR-LOAD-003`)

Five steps, in order, each producing an artefact:

1. **Record the guessed requests** from `T-M7-005`. This number must exist before the load test, or the comparison is retrospective fiction.
2. Run the load test.
3. `kubectl describe vpa backend-vpa -n civic-station` → commit **Target, Lower Bound, Upper Bound** to `docs/evidence/vpa-recommendation.txt`.
4. Update `resources.requests` to match the Target. Commit the change as its own commit, so the diff is the evidence.
5. Re-run the load test and **report what changed about HPA behaviour**.

**What to expect in step 5**, stated so the team knows whether their result is sane: if the guess was too high, utilisation was understated, the HPA scaled late, and correcting the request downward makes it scale *earlier* at the same offered load. If the guess was too low, the opposite. Either way the replica count at plateau changes, and explaining *why* is the deliverable.

**Engineering-notes Q6 — why VPA is in `Off` mode.** The failure loop, concretely: VPA raises the CPU request → HPA's computed utilisation (usage ÷ request) drops → HPA scales in → per-pod load rises → VPA raises the request again. Two controllers acting on the same signal in opposite directions. Recommender mode plus a human decision is current industrial practice for exactly this reason.

---

## 5. Zero-downtime rolling update (`FR-LOAD-004`)

**Required, not a bonus.** The brief states this in the body of §3.3 at `:293` — "Demonstrate a zero-downtime rollout" — as well as listing it as a `+4` bonus at `:486`, and `NFR-REL-003` is a `MUST` whose only measure is this demonstration. `AD-012` moves it into scope. It is nearly free once the pieces exist: SIGTERM drain (`FR-BE-021`), the 5-second `preStop` delay and `maxUnavailable: 0` (`FR-K8S-011`).

Procedure: start k6 at the plateau load of **40 VUs for at least 60 seconds** → `kubectl set image deployment/backend backend=<new SHA>` → watch `kubectl rollout status` → stop k6 → **report the failed-request count, which must be zero, alongside the number of requests attempted** (roughly 2 000 at that rate).

**The attempt count is not optional.** "Zero failures" without a denominator is compatible with having sent four requests. Both numbers go in `docs/evidence/zero-downtime.txt`.

If it is not zero, the cause is almost always one of three things, in this order of likelihood: the `preStop` delay is shorter than endpoint propagation; `CMD` is in shell form so the process never receives SIGTERM (`FR-CTR-001`); or the drain does not wait for in-flight requests. Diagnose in that order.

This is also a strong candidate for the §5.2 Q8 failure write-up, because it fails in a way that looks like a Kubernetes problem and is usually a Dockerfile problem.

---

## 6. Multi-replica rate-limiter check (`FR-CACHE-007`)

With **4 backend replicas** behind one Service, issue **30 `POST /api/complaints` from a single client IP inside one 60-second window** and assert **exactly 10 × 201 and 20 × 429**, each 429 carrying `Retry-After`.

**Exact counts, not "the configured aggregate rate".** An in-process limiter would allow 40 — four times the limit — and would pass any assertion phrased approximately. The exact numbers are what make this test the one that distinguishes a correct implementation from the common wrong one.

This is the only test that can prove the limiter is genuinely distributed, because it cannot be reproduced in a single process. `NFR-SCALE-001` names it as its measure, since the k6 run drives un-rate-limited `GET` endpoints and therefore proves nothing about the limiter. Capture the output; it is the evidence behind `BR-CACHE-004` and `RUB-E-03`.

---

## 7. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| T-M9-001 | `load/k6-script.js` with ramp/plateau/drop stages, varied filters and pages | M | Dev 2 | M7 T-M7-006 | FR-LOAD-001 | Backend CPU rises above the 60 % target under the plateau |
| T-M9-002 | metrics-server installed and verified | S | Dev 2 | T-M7-001 | FR-LOAD-002 | `kubectl top pods` returns data |
| **T-M9-003** | HPA scale-out capture: `hpa -w` **piped through a timestamping filter** to `docs/evidence/hpa-watch.txt` (`AD-051`), load run, full curve including scale-down | M | Dev 2 | T-M9-001/002, T-M7-008 | FR-LOAD-002, RUB-H-05 | The file shows 2 → higher → back to 2 **with timestamps**; replicas return to 2 within 600 s of idle. `kubectl get hpa -w` emits no timestamps of its own, so without the filter the lag in `T-M9-005` cannot be computed from the evidence at all |
| T-M9-004 | `scripts/plot_scaling.py` → `replicas-vs-load.png` | S | Dev 2 | T-M9-003 | AD-044 | Chart regenerates from committed inputs |
| T-M9-005 | Lag measured and written up (notes Q5): the difference between the first sample where offered load rises in `k6-timeseries.json` and the first where `replicas` rises in `hpa-watch.txt` | S | Dev 1 | T-M9-003, T-M9-001 | NFR-SCALE-004, RUB-J-05 | A number in seconds, derivable by a reader from the two committed files, plus where it went component by component (metrics-server scrape interval, HPA sync period, scheduling, pod start) |
| **T-M9-006** | VPA loop: guess recorded → load → recommendation committed → requests updated → re-run → report | M | Dev 2 | T-M7-009, T-M9-003 | FR-LOAD-003, RUB-H-06 | `vpa-recommendation.txt` committed; a commit diff shows the request change |
| T-M9-007 | HPA/VPA conflict written up (notes Q6) | S | Dev 2 | T-M9-006 | NFR-SCALE-005 | Describes the feedback loop concretely, not generically |
| T-M9-008 | Multi-replica rate-limiter proof | S | Dev 2 | T-M7-008, M4 T-M4-004 | FR-CACHE-007, BR-CACHE-004, RUB-E-03 | With 4 pods: exactly 10 × 201 and 20 × 429 out of 30, each 429 with `Retry-After`; captured |
| **T-M9-009** | Zero-downtime rollout under load (**required**, `AD-012`) | M | Dev 2 | T-M7-010, M2 T-M2-012 | FR-LOAD-004, NFR-REL-003, RUB-X-01 | k6 reports zero failed requests during `set image`, **with the attempt count stated** |

---

## 8. Evidence manifest produced by this module

```
docs/evidence/
├── hpa-watch.txt                 replicas rising and falling, timestamped
├── replicas-vs-load.png          generated by scripts/plot_scaling.py
├── k6-summary.json               offered load, latency, error count
├── vpa-recommendation.txt        Target / Lower Bound / Upper Bound
├── ratelimit-multireplica.txt    429 at the configured aggregate rate, 4 pods
└── zero-downtime-rollout.txt     k6 error count = 0 during set image  (bonus)
```
