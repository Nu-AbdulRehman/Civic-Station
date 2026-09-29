// The footer names the running build and classifier from GET /api/version, and a failed call
// leaves a plain footer rather than an error.
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import SiteFooter from "../src/components/SiteFooter";

afterEach(() => vi.unstubAllGlobals());

it("shows the short commit SHA and the classifier label", async () => {
  const body = { version: "0123456789abcdef0123456789abcdef01234567", provider: "llm:groq" };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));
  render(<SiteFooter />);
  expect(await screen.findByText("0123456")).toHaveAttribute("title", body.version);
  expect(screen.getByTestId("site-footer")).toHaveTextContent("classifier: Groq (hosted model)");
});

it("renders without the version line when the call fails", async () => {
  const fetch = vi.fn(async () => new Response("{}", { status: 503 }));
  vi.stubGlobal("fetch", fetch);
  render(<SiteFooter />);
  await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(screen.getByTestId("site-footer")).toHaveTextContent(/^Civic-Station$/);
});
