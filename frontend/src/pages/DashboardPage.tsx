import { useEffect, useState } from "react";
import { ApiError, type Complaint, type ComplaintPage, listComplaints } from "../api/client";
import { humanise, PROVIDER_LABEL } from "../api/labels";
import ErrorBanner from "../components/ErrorBanner";
import FilterBar, { type Filters } from "../components/FilterBar";
import Pagination from "../components/Pagination";
import StatusControl from "../components/StatusControl";

export const PAGE_SIZE = 20; // fixed and well under the API's cap of 100 (AD-015)

/** Server-side list, filters and pagination: every change is a new request, never a slice of
 *  rows already in the browser (FR-FE-006, FR-FE-007). */
export default function DashboardPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    const controller = new AbortController(); // a newer query cancels the older one
    listComplaints({ ...filters, page, pageSize: PAGE_SIZE }, controller.signal)
      .then(setData)
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        if (e instanceof ApiError) setError(e);
        else throw e;
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filters, page]);

  // Loading and error are reset where the change happens, not inside the effect, so a new
  // query costs one render rather than a cascade.
  function startQuery() {
    setLoading(true);
    setError(null);
  }

  function changeFilters(next: Filters) {
    startQuery();
    setFilters(next);
    setPage(1); // a new filter starts from the first page
  }

  function changePage(next: number) {
    startQuery();
    setPage(next);
  }

  function replace(updated: Complaint) {
    // In place, no reload: the server's returned row is the new truth (FR-FE-008).
    setData((current) =>
      current && {
        ...current,
        items: current.items.map((c) => (c.id === updated.id ? updated : c)),
      },
    );
  }

  return (
    <section>
      <h2>Complaints</h2>
      <FilterBar filters={filters} onChange={changeFilters} />
      {error && <ErrorBanner error={error} />}
      {loading && (
        <p role="status" data-testid="loading">
          Loading…
        </p>
      )}
      {data && (
        <>
          {data.items.length === 0 ? (
            <p className="muted" data-testid="empty">
              No complaints match these filters.
            </p>
          ) : (
            <table className="complaints">
              <thead>
                <tr>
                  <th>Reported</th>
                  <th>Complaint</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Classified by</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.id} data-testid="complaint-row">
                    <td>{new Date(c.created_at).toLocaleString()}</td>
                    <td>
                      <strong>{c.ai_summary}</strong>
                      <div className="muted">{c.location}</div>
                    </td>
                    <td>{humanise(c.category)}</td>
                    <td>
                      <span className={`pill pill-priority-${c.priority}`}>{c.priority}</span>
                    </td>
                    <td>{PROVIDER_LABEL[c.triaged_by]}</td>
                    <td>
                      <StatusControl complaint={c} onChanged={replace} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={changePage} />
        </>
      )}
    </section>
  );
}
