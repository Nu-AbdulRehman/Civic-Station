import { vi } from "vitest";

vi.mock("../src/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/api/client")>()),
  listComplaints: vi.fn(),
  changeStatus: vi.fn(),
}));
