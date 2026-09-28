// FR-FE-005 / FR-FE-013: three visibly different failure states, each carrying the request id.
import "./submitMock";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError, createComplaint } from "../src/api/client";
import SubmitPage from "../src/pages/SubmitPage";
import { VALID_LOCATION, VALID_TEXT } from "./fixtures";

beforeEach(() => {
  vi.mocked(createComplaint).mockReset(); // block body: a returned function would run as teardown
});

async function submitValid() {
  const user = userEvent.setup();
  render(<SubmitPage />);
  await user.type(screen.getByLabelText("What is the problem?"), VALID_TEXT);
  await user.type(screen.getByLabelText("Where is it?"), VALID_LOCATION);
  await user.click(screen.getByTestId("submit"));
}

it("maps a 400's field errors back onto the offending input", async () => {
  vi.mocked(createComplaint).mockRejectedValue(
    new ApiError(400, "validation_error", "Request validation failed.", "req-400", [
      {
        field: "location",
        rule: "string_too_short",
        detail: "String should have at least 3 characters",
      },
    ]),
  );
  await submitValid();
  const error = await screen.findByTestId("error-field");
  expect(error).toHaveAttribute("data-field", "location");
  expect(error).toHaveTextContent("String should have at least 3 characters");
  expect(screen.queryByTestId("error-ratelimit")).not.toBeInTheDocument();
  expect(screen.queryByTestId("error-generic")).not.toBeInTheDocument();
});

it("shows a distinct rate-limit state with the Retry-After seconds", async () => {
  vi.mocked(createComplaint).mockRejectedValue(
    new ApiError(429, "rate_limited", "Too many submissions.", "req-429", [], 42),
  );
  await submitValid();
  const notice = await screen.findByTestId("error-ratelimit");
  expect(notice).toHaveTextContent("wait 42 seconds");
  expect(notice).toHaveTextContent("req-429");
  expect(screen.queryByTestId("error-generic")).not.toBeInTheDocument();
});

it("shows a non-silent generic error with the request id for anything else", async () => {
  vi.mocked(createComplaint).mockRejectedValue(
    new ApiError(500, "internal_error", "Internal server error.", "req-500"),
  );
  await submitValid();
  const banner = await screen.findByTestId("error-generic");
  expect(banner).toHaveTextContent("Internal server error.");
  expect(banner).toHaveTextContent("req-500");
  expect(screen.queryByTestId("error-ratelimit")).not.toBeInTheDocument();
});
