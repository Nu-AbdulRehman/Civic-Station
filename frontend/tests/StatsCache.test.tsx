// FR-FE-010 / FR-FE-011: every count renders (zeroes included), and the badge tells the truth
// about X-Cache across two loads.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { getStats, type Stats } from "../src/api/client";
import StatsPage from "../src/pages/StatsPage";

vi.mock("../src/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/api/client")>()),
  getStats: vi.fn(),
}));

const STATS: Stats = {
  total: 3,
  by_category: { water: 2, electricity: 0, sanitation: 1, roads: 0, streetlights: 0, other: 0 },
  by_priority: { high: 2, normal: 1, low: 0 },
  by_status: { open: 3, in_progress: 0, resolved: 0, rejected: 0 },
  generated_at: "2026-09-26T08:00:00Z",
};

beforeEach(() => {
  vi.mocked(getStats).mockReset();
});

it("shows MISS on the first load and HIT on the second", async () => {
  vi.mocked(getStats)
    .mockResolvedValueOnce({ stats: STATS, cache: "MISS" })
    .mockResolvedValueOnce({ stats: STATS, cache: "HIT" });
  const user = userEvent.setup();
  render(<StatsPage />);
  expect(await screen.findByTestId("cache-badge")).toHaveTextContent("MISS");

  await user.click(screen.getByRole("button", { name: "Refresh" }));
  expect(await screen.findByText("HIT")).toHaveAttribute("data-testid", "cache-badge");
  expect(getStats).toHaveBeenCalledTimes(2);
});

it("renders the total and every key, including explicit zeroes", async () => {
  vi.mocked(getStats).mockResolvedValue({ stats: STATS, cache: "MISS" });
  render(<StatsPage />);
  expect(await screen.findByTestId("stats-total")).toHaveTextContent("3");
  expect(screen.getByTestId("count-water")).toHaveTextContent("2");
  expect(screen.getByTestId("count-electricity")).toHaveTextContent("0");
  expect(screen.getByTestId("count-low")).toHaveTextContent("0");
  expect(screen.getByTestId("count-rejected")).toHaveTextContent("0");
  expect(screen.getAllByTestId(/^count-/)).toHaveLength(6 + 3 + 4);
});
