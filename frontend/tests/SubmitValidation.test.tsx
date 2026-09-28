// FR-FE-002: client validation mirrors the server and blocks the request.
import "./submitMock";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { createComplaint } from "../src/api/client";
import SubmitPage from "../src/pages/SubmitPage";
import { VALID_LOCATION } from "./fixtures";

beforeEach(() => {
  vi.mocked(createComplaint).mockReset(); // block body: a returned function would run as teardown
});

it("blocks a 9-character complaint with a message naming the field, and sends nothing", async () => {
  const user = userEvent.setup();
  render(<SubmitPage />);
  await user.type(screen.getByLabelText("What is the problem?"), "123456789");
  await user.type(screen.getByLabelText("Where is it?"), VALID_LOCATION);
  await user.click(screen.getByTestId("submit"));

  const error = screen.getByTestId("error-field");
  expect(error).toHaveAttribute("data-field", "text");
  expect(error).toHaveTextContent("Complaint must be 10–2000 characters");
  expect(screen.getByLabelText("What is the problem?")).toHaveAttribute("aria-invalid", "true");
  expect(createComplaint).not.toHaveBeenCalled();
});

it("measures length after trimming, as the server does", async () => {
  const user = userEvent.setup();
  render(<SubmitPage />);
  await user.type(screen.getByLabelText("What is the problem?"), "    123456789     ");
  await user.type(screen.getByLabelText("Where is it?"), VALID_LOCATION);
  await user.click(screen.getByTestId("submit"));
  expect(screen.getByTestId("error-field")).toHaveTextContent("currently 9");
  expect(createComplaint).not.toHaveBeenCalled();
});
