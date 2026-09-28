// FR-FE-004: on 201, the server's category, priority, summary and provider are rendered.
import "./submitMock";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { createComplaint } from "../src/api/client";
import SubmitPage from "../src/pages/SubmitPage";
import { COMPLAINT, VALID_LOCATION, VALID_TEXT } from "./fixtures";

it("renders the triage outcome verbatim, with a human-readable provider", async () => {
  vi.mocked(createComplaint).mockResolvedValue(COMPLAINT);
  const user = userEvent.setup();
  render(<SubmitPage />);
  await user.type(screen.getByLabelText("What is the problem?"), VALID_TEXT);
  await user.type(screen.getByLabelText("Where is it?"), VALID_LOCATION);
  await user.type(screen.getByLabelText("Contact (optional)"), "  0300-1234567 ");
  await user.click(screen.getByTestId("submit"));

  expect(await screen.findByTestId("result-category")).toHaveTextContent("water");
  expect(screen.getByTestId("result-priority")).toHaveTextContent("high");
  expect(screen.getByTestId("result-summary")).toHaveTextContent(COMPLAINT.ai_summary);
  expect(screen.getByTestId("result-provider")).toHaveTextContent("keyword rules (fallback)");
  // Exactly the three contract fields are sent: no category, priority or status (FR-FE-001).
  expect(vi.mocked(createComplaint).mock.calls[0]?.[0]).toEqual({
    text: VALID_TEXT,
    location: VALID_LOCATION,
    reporter_contact: "0300-1234567",
  });
});
