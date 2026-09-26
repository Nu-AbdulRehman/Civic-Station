import type { CacheState } from "../api/client";

/** Where the numbers came from, straight from the X-Cache header (FR-FE-011). */
export default function CacheBadge({ cache, fetchedAt }: { cache: CacheState; fetchedAt: Date }) {
  return (
    <p className="cache">
      <span className={`badge badge-${cache.toLowerCase()}`} data-testid="cache-badge">
        {cache}
      </span>{" "}
      <span className="muted">
        {cache === "HIT" ? "served from cache" : "computed now"} · fetched{" "}
        {fetchedAt.toLocaleTimeString()}
      </span>
    </p>
  );
}
