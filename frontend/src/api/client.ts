// The ONLY module that issues HTTP (FR-FE-012). Components receive data and callbacks.
//
// Base path is the literal "/api": the bundle never knows a backend address; nginx proxies
// it (ADR-0002). No client-side timeout: the server's worst case is ~21 s of triage and the
// loading state is built for it (FR-FE-003). Callers pass an AbortSignal to cancel on unmount.

import type { components } from "./types";

type Schemas = components["schemas"];
export type Complaint = Schemas["Complaint"];
export type ComplaintCreate = Schemas["ComplaintCreate"];
export type ComplaintPage = Schemas["ComplaintPage"];
export type Stats = Schemas["Stats"];
export type ProvidersMeta = Schemas["ProvidersMeta"];
export type VersionInfo = Schemas["VersionInfo"];
export type Category = Schemas["Category"];
export type Priority = Schemas["Priority"];
export type Status = Schemas["Status"];
export type TriagedBy = Schemas["TriagedBy"];

const BASE = "/api";

export interface FieldError {
  field: string;
  rule: string;
  detail: string;
}

/** Every non-2xx response becomes one of these; components never inspect a raw response. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId: string,
    readonly fields: FieldError[] = [],
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function toApiError(response: Response, sentId: string): Promise<ApiError> {
  const requestId = response.headers.get("X-Request-ID") ?? sentId;
  const retryAfter = response.headers.get("Retry-After");
  const retryAfterSeconds = retryAfter !== null && /^\d+$/.test(retryAfter) ? Number(retryAfter) : null;
  try {
    // 00-conventions §4: { error: { code, message, fields? }, request_id }
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; fields?: FieldError[] };
      request_id?: string;
    };
    return new ApiError(
      response.status,
      body.error?.code ?? "unknown_error",
      body.error?.message ?? `Request failed with status ${response.status}.`,
      body.request_id ?? requestId,
      body.error?.fields ?? [],
      retryAfterSeconds,
    );
  } catch {
    // Not our envelope (a proxy error page, say): still a typed, non-silent error.
    return new ApiError(
      response.status,
      "unknown_error",
      `Request failed with status ${response.status}.`,
      requestId,
      [],
      retryAfterSeconds,
    );
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const requestId = crypto.randomUUID(); // FR-FE-013: one id per request, shown in errors
  const headers = new Headers(init.headers);
  headers.set("X-Request-ID", requestId);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!response.ok) throw await toApiError(response, requestId);
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await request(path, init)).json()) as T;
}

export function createComplaint(body: ComplaintCreate, signal?: AbortSignal): Promise<Complaint> {
  return json("/complaints", { method: "POST", body: JSON.stringify(body), signal });
}

export function getComplaint(id: string, signal?: AbortSignal): Promise<Complaint> {
  return json(`/complaints/${encodeURIComponent(id)}`, { signal });
}

export interface ListQuery {
  category?: Category;
  priority?: Priority;
  status?: Status;
  page?: number;
  pageSize?: number;
}

/** Filters and pagination are query parameters: the server filters, never the browser. */
export function listComplaints(query: ListQuery = {}, signal?: AbortSignal): Promise<ComplaintPage> {
  const params = new URLSearchParams();
  if (query.category) params.set("category", query.category);
  if (query.priority) params.set("priority", query.priority);
  if (query.status) params.set("status", query.status);
  if (query.page !== undefined) params.set("page", String(query.page));
  if (query.pageSize !== undefined) params.set("page_size", String(query.pageSize));
  const qs = params.toString();
  return json(`/complaints${qs ? `?${qs}` : ""}`, { signal });
}

/** Sends the attempted transition as-is; a 409's message is the server's (BR-STATUS-005). */
export function changeStatus(id: string, status: Status, signal?: AbortSignal): Promise<Complaint> {
  return json(`/complaints/${encodeURIComponent(id)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
    signal,
  });
}

export type CacheState = "HIT" | "MISS";

/** The stats body plus where it came from, read from X-Cache (FR-FE-011). */
export async function getStats(signal?: AbortSignal): Promise<{ stats: Stats; cache: CacheState }> {
  const response = await request("/stats", { signal });
  const cache = response.headers.get("X-Cache") === "HIT" ? "HIT" : "MISS";
  return { stats: (await response.json()) as Stats, cache };
}

export function getProviders(signal?: AbortSignal): Promise<ProvidersMeta> {
  return json("/meta/providers", { signal });
}

export function getVersion(signal?: AbortSignal): Promise<VersionInfo> {
  return json("/version", { signal });
}
