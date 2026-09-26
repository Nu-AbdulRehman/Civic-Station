# Engineering notes

The eight §5.2 answers are assembled here by T-M10-006. Sections are added as their owning
tasks complete; every claim cites a file and line in this repository.

---

## Indexes and the queries they serve (`FR-DATA-003`, `BR-DATA-006`, `AD-049`, T-M3-008)

Every list request is built in one place,
`backend/app/repositories/complaints.py:68-83`: optional equality filters on `category`,
`priority` and `status` (`:68-76`), always ordered `created_at DESC, id DESC` (`:81`, `AD-016`),
then `LIMIT/OFFSET` (`:82-83`). The three indexes are created in revision `0001`
(`backend/alembic/versions/0001_create_complaints.py:85-102`) and mirrored in the ORM model
(`backend/app/db/models.py:60-67`) so that `alembic check` reports no drift.

| Index | Columns | Query it serves |
|---|---|---|
| `ix_complaints_created_at_id` (`0001_create_complaints.py:86`) | `created_at DESC, id DESC` | The unfiltered Dashboard listing: `ORDER BY created_at DESC, id DESC LIMIT :n OFFSET :m`. Both columns, because the `id` tie-break is what keeps pagination stable when rows share a timestamp; the seed deliberately creates such a pair (`backend/seeds/complaints.py`, third and fourth rows). |
| `ix_complaints_status_priority_created` (`:92`) | `status, priority, created_at DESC` | The operations filter: `WHERE status = :s AND priority = :p ORDER BY created_at DESC`. Carries `created_at`, so a filtered page is one index scan rather than a scan plus a sort. |
| `ix_complaints_category_created` (`:98`) | `category, created_at DESC` | The category filter: `WHERE category = :c ORDER BY created_at DESC`. |

**Evidence, not assertion.** `backend/tests/integration/test_schema.py:134` runs `EXPLAIN` on
each named query and asserts that its index appears in the plan and that no `Sort` node does;
`:146` asserts all three exist by name, which guards against a migration being reverted.

**A known limit, left visible.** The API always adds the `id` tie-break, including on filtered
lists. For the two filtered indexes, which do not carry `id`, PostgreSQL then adds an
*Incremental Sort* over rows that share a `created_at` (observed with `EXPLAIN` on 2026-09-26:
`Presorted Key: created_at`). Only equal-timestamp runs are sorted, so the cost is small, but
`AD-049`'s "no sort" holds only for the queries as `04-M3-data.md` §2.2 names them, not for
the exact SQL the repository issues. The fix is `id DESC` as a trailing column on both
filtered indexes; it changes `AD-049` and is therefore a decision for both developers rather
than a silent edit.
