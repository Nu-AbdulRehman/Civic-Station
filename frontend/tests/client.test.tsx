// FR-FE-013 at the transport: a UUID X-Request-ID goes out on every request, and the server's
// error envelope becomes one typed ApiError carrying that id (00-conventions §4).
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, changeStatus, createComplaint, getStats } from "../src/api/client";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response) {
  const spy = vi.fn(async (_url: string, _init: RequestInit) => response);
  vi.stubGlobal("fetch", spy);
  return spy;
}

const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

it("sends a UUIDv4 X-Request-ID to a relative /api path", async () => {
  const spy = stubFetch(new Response("{}", { status: 201 }));
  await createComplaint({ text: "x".repeat(10), location: "abc" });
  const [url, init] = spy.mock.calls[0]!;
  expect(url).toBe("/api/complaints");
  expect(new Headers(init.headers).get("X-Request-ID")).toMatch(UUID4);
});

it("turns the error envelope into an ApiError with the server's message verbatim", async () => {
  const message = "Cannot transition complaint from 'resolved' to 'open'.";
  const body = { error: { code: "invalid_transition", message }, request_id: "srv-123" };
  stubFetch(new Response(JSON.stringify(body), { status: 409 }));
  const error = await changeStatus("id-1", "open").catch((e: unknown) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ status: 409, code: "invalid_transition", requestId: "srv-123" });
  expect((error as ApiError).message).toBe(message);
});

it("reads Retry-After on a 429 and X-Cache on stats", async () => {
  const limitedBody = JSON.stringify({ error: { code: "rate_limited", message: "m" } });
  stubFetch(new Response(limitedBody, { status: 429, headers: { "Retry-After": "17" } }));
  const limited = await createComplaint({ text: "x".repeat(10), location: "abc" }).catch(
    (e: unknown) => e as ApiError,
  );
  expect(limited).toBeInstanceOf(ApiError);
  expect((limited as ApiError).retryAfterSeconds).toBe(17);

  stubFetch(new Response(JSON.stringify({ total: 0 }), { headers: { "X-Cache": "HIT" } }));
  expect((await getStats()).cache).toBe("HIT");
});

it("reports a network failure as a typed error carrying the id that was sent", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }),
  );
  const error = (await getStats().catch((e: unknown) => e)) as ApiError;
  expect(error.code).toBe("network_error");
  expect(error.requestId).toMatch(UUID4);
});
