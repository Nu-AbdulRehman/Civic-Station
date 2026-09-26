import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type CacheState, getStats, type Stats } from "../api/client";
import { humanise } from "../api/labels";
import { categoryValues, priorityValues, statusValues } from "../api/types";
import CacheBadge from "../components/CacheBadge";
import ErrorBanner from "../components/ErrorBanner";

interface Loaded {
  stats: Stats;
  cache: CacheState;
  fetchedAt: Date;
}

/** Aggregates from GET /api/stats. Every enum key is present with an explicit zero (AD-025),
 *  so the tables need no fallback for a missing key (FR-FE-010). */
export default function StatsPage() {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const inFlight = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setLoading(true);
    setError(null);
    try {
      const { stats, cache } = await getStats(controller.signal);
      setLoaded({ stats, cache, fetchedAt: new Date() });
    } catch (e) {
      if (controller.signal.aborted) return;
      if (!(e instanceof ApiError)) throw e;
      setError(e);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    return () => inFlight.current?.abort();
  }, [load]);

  return (
    <section>
      <h2>Statistics</h2>
      <button type="button" onClick={() => void load()} disabled={loading}>
        {loading ? "Refreshing…" : "Refresh"}
      </button>
      {error && <ErrorBanner error={error} />}
      {loaded && (
        <>
          <CacheBadge cache={loaded.cache} fetchedAt={loaded.fetchedAt} />
          <p className="total">
            Total complaints: <strong data-testid="stats-total">{loaded.stats.total}</strong>
          </p>
          <div className="stats-grid">
            <Counts title="By category" keys={categoryValues} counts={loaded.stats.by_category} />
            <Counts title="By priority" keys={priorityValues} counts={loaded.stats.by_priority} />
            <Counts title="By status" keys={statusValues} counts={loaded.stats.by_status} />
          </div>
        </>
      )}
    </section>
  );
}

function Counts<K extends string>({
  title,
  keys,
  counts,
}: {
  title: string;
  keys: readonly K[];
  counts: Partial<Record<K, number>>;
}) {
  const id = title.toLowerCase().replace(/\s+/g, "-");
  return (
    <table className="counts" aria-labelledby={id}>
      <caption id={id}>{title}</caption>
      <tbody>
        {keys.map((key) => (
          <tr key={key} data-testid={`count-${key}`}>
            <th scope="row">{humanise(key)}</th>
            <td>{counts[key] ?? 0}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
