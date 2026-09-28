// FR-FE-008 / FR-FE-009 / BR-STATUS-005: every status is offered, the attempt is sent, and a
// 409 shows the server's message verbatim — the frontend authors no rejection of its own.
import "./dashboardMock";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError, changeStatus, type Complaint, listComplaints } from "../src/api/client";
import DashboardPage from "../src/pages/DashboardPage";
import { COMPLAINT } from "./fixtures";

const RESOLVED: Complaint = { ...COMPLAINT, status: "resolved" };
const SERVER_409 = "Cannot transition complaint from 'resolved' to 'open'.";

beforeEach(() => {
  vi.mocked(listComplaints).mockReset();
  vi.mocked(changeStatus).mockReset();
  vi.mocked(listComplaints).mockResolvedValue({
    items: [RESOLVED],
    total: 1,
    page: 1,
    page_size: 20,
  });
});

function control() {
  return screen.findByLabelText(`Status of complaint ${RESOLVED.id}`);
}

it("offers every status even on a terminal row, and sends the forbidden attempt", async () => {
  vi.mocked(changeStatus).mockRejectedValue(
    new ApiError(409, "invalid_transition", SERVER_409, "req-409"),
  );
  const user = userEvent.setup();
  render(<DashboardPage />);
  const select = await control();
  const options = within(select).getAllByRole("option") as HTMLOptionElement[];
  expect(options.map((o) => o.value)).toEqual(["open", "in_progress", "resolved", "rejected"]);
  expect(options.every((o) => !o.disabled)).toBe(true);

  await user.selectOptions(select, "open");
  expect(changeStatus).toHaveBeenCalledWith(RESOLVED.id, "open");
  // Exactly the server's text: no prefix, no suffix, no client rewording.
  expect(await screen.findByTestId("status-error")).toHaveTextContent(SERVER_409, {
    normalizeWhitespace: false,
  });
  expect(screen.getByTestId("status-error").textContent).toBe(SERVER_409);
  expect(select).toHaveValue("resolved"); // a rejected transition changed nothing
});

it("updates the row in place on success, without reloading the list", async () => {
  vi.mocked(listComplaints).mockResolvedValue({
    items: [COMPLAINT],
    total: 1,
    page: 1,
    page_size: 20,
  });
  vi.mocked(changeStatus).mockResolvedValue({ ...COMPLAINT, status: "in_progress" });
  const user = userEvent.setup();
  render(<DashboardPage />);
  const select = await screen.findByLabelText(`Status of complaint ${COMPLAINT.id}`);
  await user.selectOptions(select, "in_progress");
  expect(select).toHaveValue("in_progress");
  expect(listComplaints).toHaveBeenCalledTimes(1);
  expect(screen.queryByTestId("status-error")).not.toBeInTheDocument();
});
