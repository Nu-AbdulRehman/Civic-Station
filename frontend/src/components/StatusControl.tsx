import { useState } from "react";
import { ApiError, changeStatus, type Complaint, type Status } from "../api/client";
import { humanise } from "../api/labels";
import { statusValues } from "../api/types";

/**
 * Offers EVERY status, including ones the server will refuse: the frontend does not know the
 * state machine and does not pre-empt it (BR-STATUS-005, FR-FE-008). A refused attempt shows
 * the server's own 409 message, verbatim (FR-FE-009) — there is no client-authored rejection.
 */
export default function StatusControl({
  complaint,
  onChanged,
}: {
  complaint: Complaint;
  onChanged: (updated: Complaint) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function attempt(target: Status) {
    setPending(true);
    setError(null);
    try {
      onChanged(await changeStatus(complaint.id, target));
    } catch (e) {
      if (!(e instanceof ApiError)) throw e;
      setError(e);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="status-control">
      <select
        className={`pill pill-status-${complaint.status}`}
        aria-label={`Status of complaint ${complaint.id}`}
        value={complaint.status}
        disabled={pending}
        onChange={(e) => void attempt(e.target.value as Status)}
      >
        {statusValues.map((value) => (
          <option key={value} value={value}>
            {humanise(value)}
          </option>
        ))}
      </select>
      {error && (
        <p role="alert" className="field-error" data-testid="status-error">
          {error.message}
          {error.status !== 409 && <span className="request-id"> (request {error.requestId})</span>}
        </p>
      )}
    </div>
  );
}
