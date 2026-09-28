// FR-FE-006 / FR-FE-007: pagination and filters are server-side — every change is a request.
import "./dashboardMock";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { type ComplaintPage, listComplaints } from "../src/api/client";
import DashboardPage from "../src/pages/DashboardPage";
import { COMPLAINT } from "./fixtures";

function pageOf(page: number, total: number): ComplaintPage {
  return { items: [{ ...COMPLAINT, id: `id-${page}` }], total, page, page_size: 20 };
}

beforeEach(() => {
  vi.mocked(listComplaints).mockReset();
  vi.mocked(listComplaints).mockImplementation(async (query = {}) => pageOf(query.page ?? 1, 45));
});

function lastQuery() {
  return vi.mocked(listComplaints).mock.calls.at(-1)?.[0];
}

it("renders the server's total and requests the next page from the server", async () => {
  const user = userEvent.setup();
  render(<DashboardPage />);
  expect(await screen.findByTestId("page-info")).toHaveTextContent("Page 1 of 3 · 45 complaints");
  expect(lastQuery()).toEqual({ page: 1, pageSize: 20 });

  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByText("Page 2 of 3 · 45 complaints", { exact: false })).toBeVisible();
  expect(lastQuery()).toEqual({ page: 2, pageSize: 20 });
  expect(listComplaints).toHaveBeenCalledTimes(2);
});

it("sends filters as query parameters and resets to page 1", async () => {
  const user = userEvent.setup();
  render(<DashboardPage />);
  await screen.findByTestId("page-info");
  await user.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("Page 2 of 3", { exact: false });

  await user.selectOptions(screen.getByLabelText("Filter by status"), "open");
  await user.selectOptions(screen.getByLabelText("Filter by priority"), "high");
  expect(lastQuery()).toEqual({ status: "open", priority: "high", page: 1, pageSize: 20 });
});

it("offers the server's vocabulary as filter options", async () => {
  render(<DashboardPage />);
  const category = await screen.findByLabelText("Filter by category");
  const options = within(category)
    .getAllByRole("option")
    .map((o) => (o as HTMLOptionElement).value);
  expect(options).toEqual(["", "water", "electricity", "sanitation", "roads", "streetlights", "other"]);
});
