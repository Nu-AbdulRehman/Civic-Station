// FR-FE-017: a view that throws during render yields a recoverable UI, not a blank page, and
// the rest of the shell (navigation) is still there.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";

const crash = vi.hoisted(() => ({ on: true }));

vi.mock("../src/pages/SubmitPage", () => ({
  default: function ExplodingSubmitPage() {
    if (crash.on) throw new Error("render failure");
    return <h2>Report a problem</h2>;
  },
}));
vi.mock("../src/pages/StatsPage", () => ({ default: () => <h2>Statistics</h2> }));

beforeEach(() => {
  crash.on = true;
  vi.spyOn(console, "error").mockImplementation(() => undefined); // React logs the caught error
  window.addEventListener("error", swallow); // React's dev build re-reports it to jsdom
});

function swallow(event: ErrorEvent) {
  event.preventDefault();
}
afterEach(() => {
  vi.restoreAllMocks();
  window.removeEventListener("error", swallow);
});

it("contains the crash, keeps the navigation, and recovers on reset", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();

  crash.on = false;
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Report a problem" })).toBeInTheDocument();
});

it("recovers by navigating to another view", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Stats" }));
  expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Statistics" })).toBeInTheDocument();
});
