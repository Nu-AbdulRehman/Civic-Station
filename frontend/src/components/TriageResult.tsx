import type { Complaint } from "../api/client";
import { humanise, PROVIDER_LABEL } from "../api/labels";

/** Renders the server's triage values verbatim; nothing here is computed (FR-FE-004). */
export default function TriageResult({ complaint }: { complaint: Complaint }) {
  return (
    <section className="result" data-testid="triage-result" aria-live="polite">
      <h3>Your report was received</h3>
      <dl>
        <dt>Category</dt>
        <dd data-testid="result-category">{humanise(complaint.category)}</dd>
        <dt>Priority</dt>
        <dd data-testid="result-priority">{complaint.priority}</dd>
        <dt>Summary</dt>
        <dd data-testid="result-summary">{complaint.ai_summary}</dd>
        <dt>Classified by</dt>
        <dd data-testid="result-provider">{PROVIDER_LABEL[complaint.triaged_by]}</dd>
      </dl>
      <p className="muted">Reference: {complaint.id}</p>
    </section>
  );
}
