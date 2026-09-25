# 04 — M3 Data layer: design and implementation guide

**Owner:** Dev 1 (`AD-013`)
**Depends on:** `00-conventions.md`, M2 domain enums
**Delivers:** `RUB-D-01`…`RUB-D-04`, and the durability half of `RUB-G-04` and `RUB-H-01`. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** PostgreSQL 16, Alembic, SQLAlchemy 2.0 async with typed `Mapped[...]` models (`AD-032`)

---

## 1. What this module is for

Durable state, and a schema that changes by review rather than by hope. The brief's line is the whole design brief: *a migration is a versioned, reviewable, reversible change; a startup script is a hope.*

The second job of this layer is to be the last line of defence for the domain rules. Application validation protects the user experience; database constraints protect the data from every future code path — a seed script, a maintenance query, a migration written at 2am.

---

## 2. Schema design

### 2.1 The `complaints` table

Columns per `FR-DATA-002`, with the decisions from Round 2 applied:

| Column | Type | Constraint |
|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` (`AD-021`) |
| `text` | `text` | `NOT NULL`, `CHECK (char_length(text) BETWEEN 10 AND 2000)` |
| `location` | `text` | `NOT NULL`, `CHECK (char_length(location) BETWEEN 3 AND 200)` |
| `reporter_contact` | `text` | nullable, `CHECK (char_length(reporter_contact) <= 200)` — bounded, because an unbounded free-text field is an unbounded storage and log-exposure surface, and this is the most sensitive column in the table |
| `category` | `complaint_category` | `NOT NULL` — native enum (`AD-020`) |
| `priority` | `complaint_priority` | `NOT NULL` — native enum |
| `status` | `complaint_status` | `NOT NULL`, default `'open'` — native enum |
| `ai_summary` | `text` | **`NOT NULL`**, `CHECK (char_length(ai_summary) <= 140)` |
| `triaged_by` | `varchar(32)` | `NOT NULL`, `CHECK (triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback','simulated'))` (`AD-020`) |
| `triage_confidence` | `double precision` | **`NOT NULL`**, `CHECK (triage_confidence BETWEEN 0 AND 1)` (`AD-026`) |
| `triage_latency_ms` | `integer` | `NOT NULL`, `CHECK (>= 0)` |
| `created_at` | `timestamptz` | `NOT NULL`, default `now()` |
| `updated_at` | `timestamptz` | `NOT NULL`, default `now()`, `CHECK (updated_at >= created_at)` |

**Three constraints were previously under-specified, and each mattered.**

**`ai_summary` and `triage_confidence` are `NOT NULL`.** `AD-023` and `AD-026` make every provider populate both, including the rules path, and `01-api-contract.md` §1 states them as non-nullable in the response. A column left nullable would let the database accept a row the contract says cannot exist — the guarantee would live only in the code that happens to write it.

**The `triaged_by` `CHECK` set is written out in full.** It previously read `IN (...)`, a literal ellipsis, so the allowed values were unspecified in the document that owns them. `'simulated'` is in the set because CI runs `TRIAGE_PROVIDER=simulated` and a successful simulated triage must persist a legal, truthful value; without it every CI test that creates a complaint fails the constraint.

**`updated_at >= created_at`** is enforced in the database, because `BR-STATUS-006` depends on the ordering and the application is the only thing maintaining it.

**On trimming.** The application strips leading and trailing whitespace **before** validating, and the trimmed value is what is persisted. Stated because `01-api-contract.md` §2 validates "10–2000 characters after trimming" while this `CHECK` measures what is stored — if the application stored the untrimmed string, a whitespace-padded 2000-character body would pass validation and fail the constraint.

**Retention: none, deliberately.** Rows are kept indefinitely. There is no `DELETE` endpoint, no anonymisation job and no retention column — including for `reporter_contact`, which is the most sensitive field in the table. The consequence is worth stating rather than leaving to inference: the contact field is protected **in transit** (never sent to a model, `BR-TRIAGE-015`) and **not** protected in storage, and a citizen cannot have their complaint removed. `ADR-0004` and `docs/NON-GOALS.md` §4 record this as a scope decision with what the fix would take; it depends on authentication, which is also out of scope, because an unauthenticated delete endpoint would be worse than none.

**One entity, no relationships, no history.** The operator who performs a transition is not modelled — there is no operator identity anywhere in the system (`AD-056`) — and there is no `status_transitions` audit table, so `updated_at` is the only trace that a state change happened at all. Both follow from authentication being out of scope, and both are in `docs/NON-GOALS.md` §1 with the table a fix would add.

**Why enums differ by column.** `category`, `priority` and `status` are closed sets that will not change during this project, so a native PostgreSQL enum gives the strongest guarantee. `triaged_by` grows every time a provider is added, and `ALTER TYPE` inside a reversible Alembic revision is awkward — so it is `varchar` with a `CHECK`, which a migration can widen in one line and reverse in one line.

**`gen_random_uuid()`** is built in from PostgreSQL 13 onward; no `pgcrypto` extension is needed on 16. The row is returned with `RETURNING` so the id is available immediately.

**`updated_at`** is maintained by the application inside the same transaction as the mutation. A database trigger would also work; the application is chosen because `BR-STATUS-006` requires that a *rejected* transition leaves `updated_at` untouched, and a trigger that fires on any `UPDATE` makes that easier to get wrong.

### 2.2 Indexes (`FR-DATA-003`, `BR-DATA-006`, `AD-049`)

**Three indexes, not two.** Each is paired with the exact query it serves, and that pairing goes in the engineering notes — an unexplained index is cargo cult.

| Index | Serves |
|---|---|
| `ix_complaints_created_at_id` on `(created_at DESC, id DESC)` | The unfiltered default listing: `SELECT … ORDER BY created_at DESC, id DESC LIMIT :n OFFSET :m` (`AD-016`). **Both columns**, because the `id` tie-break is what makes pagination stable — an index on `created_at` alone leaves the sort incomplete and reintroduces the duplicate-row-across-pages bug `AD-016` exists to prevent. |
| `ix_complaints_status_priority_created` on `(status, priority, created_at DESC)` | The operations filter: `SELECT … WHERE status = :s AND priority = :p ORDER BY created_at DESC`. **Carries `created_at`**, so a filtered page is one index scan rather than an index scan plus a sort. |
| `ix_complaints_category_created` on `(category, created_at DESC)` | The category filter: `SELECT … WHERE category = :c ORDER BY created_at DESC`. `category` is a first-class filter in `FR-BE-003` and had no index at all. |

**Why this changed.** The audit found that neither of the two original indexes could serve the query the API actually issues. `01-api-contract.md` §4 filters on any subset of three columns and always orders by `created_at DESC, id DESC`: `(created_at DESC)` cannot apply the filter, `(status, priority)` cannot serve the order, and nothing covered `category`. `RUB-D-03` marks "two indexes, each justified by a named query" — three justified indexes satisfy that line, and two unjustifiable ones do not.

**Acceptance:** `EXPLAIN` on each named query shows its paired index in use with **no separate sort step**. That assertion is the point; an index that exists and is not used is worse than none, because it costs writes and buys nothing.

State all three pairings, with file and line references, in `ENGINEERING-NOTES.md`.

### 2.3 Migration discipline

- **Revision `0001`** creates the enum types, the table and all three indexes. **Revision `0002`** is reserved for the first schema change after implementation begins. One revision changes one logical thing (`NFR-MAINT-004`); the earlier wording — "a second *may* add indexes if the first is already merged" — left it ambiguous whether `0002` exists, while `T-M3-004` assumed it did. Every revision has a working `downgrade` (`AD-033`).
- Native enum types must be **created in `upgrade` and dropped in `downgrade` explicitly** — Alembic's autogenerate does not always emit the `DROP TYPE`, and a downgrade that leaves the type behind makes the next upgrade fail. This is the single most common Alembic failure in this shape of project.
- Migrations are run as a deliberate step, never from application startup (`BR-DATA-001`). In Compose this is a one-shot command clearly separate from serving; **on Kubernetes it is an init container on the backend Deployment** (`08-M7-kubernetes.md`) — chosen over a Job because it needs no separate ordering mechanism and cannot be forgotten, at the cost of running once per pod, which is safe because Alembic is idempotent.
- **Every revision must be backward-compatible with the previous application version.** The init container migrates before the new pod starts, while `maxUnavailable: 0` keeps old pods serving, so for the duration of a rollout the **old code runs against the new schema**. That means expand-then-contract: add nullable columns and new tables in the release that starts writing them; drop or narrow only in a later release, after no running code references them. This was previously unstated, and it is the constraint that turns a routine migration into an outage.
- CI proves reversibility: migrate up from empty, down to base, up again. It also starts the previous image against the new schema to prove the compatibility rule above.

---

## 3. Seed data (`FR-DATA-004`)

**Exactly 30** complaints in Urdu-influenced English, with this distribution, so "a realistic mix" is a checklist rather than a judgement:

| Dimension | Required counts |
|---|---|
| Category | ≥ 4 in each of the six |
| Priority | ≥ 8 `high`, ≥ 8 `normal`, ≥ 8 `low` |
| Status | **12 `open`, 8 `in_progress`, 6 `resolved`, 4 `rejected`** |

The status spread is not decoration. The Dashboard's 409 demonstration needs a **terminal** row to attempt an invalid transition against, and a table of 30 identical `open` rows demonstrates neither the filters nor the state machine.

**Idempotency (`AD-022`):** each seed row's id is `uuid5(SEED_UUID_NAMESPACE, complaint_text)` where the namespace is the **fixed literal `6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63`**. It was previously written as `NAMESPACE`, a placeholder — and a placeholder namespace means ids differ per machine, so the "provably unchanged on a second run" claim held only within one checkout. Insert with `ON CONFLICT (id) DO NOTHING`.

**The seed is an explicit exemption** from `BR-VAL-006` (server-generated ids), `BR-STATUS-001` (initial status `open`) and `BR-DATA-003` (SQL only in `repositories/`). Each of those rules now names the exemption. A seed is an administrative fixture loader that runs before the system serves anyone; it is not a client, and no request path can reach it.

**Content guidance.** The dashboard demo is worth more than the row count. Write complaints that sound like real reports: *"Sui gas pressure very low since two days in Street 7, cooking not possible in morning"*, *"Manhole cover missing near Chowk, children playing there, very dangerous"*. Include at least one that is genuinely ambiguous between categories, and at least one containing a phone number — the latter is the fixture the redaction test (`ADR-0004`) uses.

**Seeded rows carry `triaged_by = "rules"`** and a plausible `triage_latency_ms`, because they were not produced by a model. Inventing `llm:groq` attribution for rows no model ever saw would make `BR-VOCAB-004` false.

---

## 4. Persistence contract (`FR-DATA-005`)

Two demonstrations, both on video:

1. `docker compose down` then `docker compose up` — row count and a known id survive, because `pgdata` is a named volume.
2. `kubectl delete pod postgres-0` — the StatefulSet recreates it and the PVC reattaches, so the rows survive.

Note for the second: only `docker compose down -v` destroys data. The CI integration job uses `-v` deliberately, to start clean; the persistence demo must not.

---

## 5. Invariants this module must not violate

| Rule | Where it bites |
|---|---|
| `BR-DATA-001` | No `create_all`, no DDL outside `alembic/versions/` |
| `BR-DATA-002` | Length, enum and range rules exist as database constraints, not only in Pydantic |
| `BR-DATA-004` | Seed is idempotent by construction, not by convention |
| `BR-VAL-006`, `BR-VAL-007` | Server-generated id; UTC `timestamptz` |
| `BR-VOCAB-001…004` | Enum values match the domain module exactly, including `triaged_by`'s allowed set |

---

## 6. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M3-001** | Alembic scaffolding: `alembic.ini`, env configured for the async engine, revision directory | S | Dev 1 | T-M2-003 | FR-DATA-001 | `alembic upgrade head` runs against an empty database |
| **T-M3-002** | Revision 0001: enum types + `complaints` table + all `CHECK` constraints, with a working `downgrade` that drops the types | M | Dev 1 | T-M3-001, T-M2-002 | FR-DATA-002, BR-DATA-002 | up → down → up cycle succeeds; inserting a 9-character text is rejected **by the database** |
| T-M3-003 | SQLAlchemy `Mapped[...]` ORM model matching the migration | S | Dev 1 | T-M3-002 | AD-032 | Model and migration agree; autogenerate produces an empty diff |
| T-M3-004 | Revision 0002: the two indexes | S | Dev 1 | T-M3-002 | FR-DATA-003 | Indexes exist; `EXPLAIN` on the two named queries uses them |
| T-M3-005 | Seed command: ≥ 30 complaints, UUIDv5 ids, `ON CONFLICT DO NOTHING` | M | Dev 1 | T-M3-003 | FR-DATA-004, BR-DATA-004 | Run twice → identical `count(*)` and identical ids |
| T-M3-006 | Migration step wired into Compose and documented (not in startup code) | S | Dev 1 | T-M3-002 | BR-DATA-001 | `docker compose up` yields a migrated, seeded database; no DDL in `app/` |
| T-M3-007 | CI job step: up → down → up, plus seed-twice assertion | S | Dev 1 | T-M3-005 | NFR-MAINT-004 | CI fails if a `downgrade` is missing or broken |
| T-M3-008 | Index justification written into `ENGINEERING-NOTES.md` with file:line references | S | Dev 1 | T-M3-004, M2 T-M2-006 | BR-DATA-006, RUB-D-03 | Each index has a named query and a line reference |
| T-M3-009 | Persistence demonstrations captured (Compose cycle, pod delete) | S | Dev 2 | T-M3-006, M7 | FR-DATA-005 | Two captures in `docs/evidence/` |

---

## 7. Test plan

- **Constraint tests (integration):** text too short, text too long, location too short, `ai_summary` over 140, `triage_confidence` of 1.5, an invalid `triaged_by` value — each rejected by the database, asserted by catching the integrity error rather than by validating in Python first.
- **Migration test (CI):** up, down, up.
- **Seed test:** run twice, assert `count(*)` and the set of ids are unchanged.
- **Index test:** assert the two indexes exist by name (a cheap regression guard against a migration being reverted by accident).
- **Ordering test:** insert rows sharing a `created_at`, page through them, assert no id appears twice — this is what the `id` tie-break exists for.
