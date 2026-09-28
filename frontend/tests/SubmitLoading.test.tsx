// FR-FE-003: the loading state is honest for the whole request, including the 21 s worst case.
import "./submitMock";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { type Complaint, createComplaint } from "../src/api/client";
import SubmitPage from "../src/pages/SubmitPage";
import { COMPLAINT, deferred, VALID_LOCATION, VALID_TEXT } from "./fixtures";

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(createComplaint).mockReset();
});
afterEach(() => vi.useRealTimers());

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText("What is the problem?"), {
    target: { value: VALID_TEXT },
  });
  fireEvent.change(screen.getByLabelText("Where is it?"), { target: { value: VALID_LOCATION } });
  fireEvent.click(screen.getByTestId("submit"));
}

it("keeps the control disabled and the indicator up for a 21-second request", async () => {
  const pending = deferred<Complaint>();
  vi.mocked(createComplaint).mockReturnValue(pending.promise);
  render(<SubmitPage />);
  fillAndSubmit();

  expect(screen.getByTestId("submit")).toBeDisabled();
  expect(screen.getByTestId("loading")).toHaveTextContent("Classifying your report");

  await act(() => vi.advanceTimersByTimeAsync(21_000)); // no client timeout gives up early
  expect(screen.getByTestId("submit")).toBeDisabled();
  expect(screen.getByTestId("loading")).toBeInTheDocument();
  fireEvent.click(screen.getByTestId("submit"));
  expect(createComplaint).toHaveBeenCalledTimes(1); // no double submission

  await act(async () => pending.resolve(COMPLAINT));
  expect(screen.getByTestId("submit")).toBeEnabled();
  expect(screen.queryByTestId("loading")).not.toBeInTheDocument();
});

it("aborts the in-flight request when the page unmounts", () => {
  vi.mocked(createComplaint).mockReturnValue(deferred<Complaint>().promise);
  const { unmount } = render(<SubmitPage />);
  fillAndSubmit();
  const signal = vi.mocked(createComplaint).mock.calls[0]?.[1];
  expect(signal?.aborted).toBe(false);
  unmount();
  expect(signal?.aborted).toBe(true);
});
