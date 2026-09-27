import type { Category, Priority, Status } from "../api/client";
import { humanise } from "../api/labels";
import { categoryValues, priorityValues, statusValues } from "../api/types";

export interface Filters {
  category?: Category;
  priority?: Priority;
  status?: Status;
}

// Options come from the generated enum arrays: the server's vocabulary, never a hand-written
// list that could drift from it (BR-VOCAB-005, FR-FE-018).
const OPTIONS = {
  category: categoryValues,
  priority: priorityValues,
  status: statusValues,
} as const;

export default function FilterBar({
  filters,
  onChange,
}: {
  filters: Filters;
  onChange: (next: Filters) => void;
}) {
  return (
    <div className="filters" role="group" aria-label="Filters">
      {(Object.keys(OPTIONS) as (keyof Filters)[]).map((name) => (
        <label key={name}>
          {humanise(name)}
          <select
            aria-label={`Filter by ${name}`}
            value={filters[name] ?? ""}
            onChange={(e) => onChange({ ...filters, [name]: e.target.value || undefined })}
          >
            <option value="">All</option>
            {OPTIONS[name].map((value) => (
              <option key={value} value={value}>
                {humanise(value)}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}
