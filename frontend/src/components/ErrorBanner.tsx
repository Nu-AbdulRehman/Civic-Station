import type { ApiError } from "../api/client";

/** The non-silent catch-all: the server's message plus the request id, so the failure can be
 *  found in the logs (FR-FE-005, FR-FE-013). */
export default function ErrorBanner({ error }: { error: ApiError }) {
  return (
    <div role="alert" className="banner error" data-testid="error-generic">
      <p>{error.message}</p>
      <p className="request-id">
        Request ID: <code>{error.requestId}</code>
      </p>
    </div>
  );
}
