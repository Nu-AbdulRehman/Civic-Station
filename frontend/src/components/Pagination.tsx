/** Renders the server's `total`; the client never holds more than one page (FR-FE-006). */
export default function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav className="pagination" aria-label="Pagination">
      <button type="button" onClick={() => onPage(page - 1)} disabled={page <= 1}>
        Previous
      </button>
      <span data-testid="page-info">
        Page {page} of {pages} · {total} complaint{total === 1 ? "" : "s"}
      </span>
      <button type="button" onClick={() => onPage(page + 1)} disabled={page >= pages}>
        Next
      </button>
    </nav>
  );
}
