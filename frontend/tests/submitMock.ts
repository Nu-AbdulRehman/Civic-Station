import { vi } from "vitest";

// Mock at the api/client boundary, not at fetch: the tests exercise the component contract,
// not the transport (02-M1 §5). ApiError stays real so instanceof checks behave.
vi.mock("../src/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/api/client")>()),
  createComplaint: vi.fn(),
}));
