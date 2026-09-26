import type { Complaint } from "../src/api/client";

export const COMPLAINT: Complaint = {
  id: "0b8f7f5e-4d9c-4a57-9d2e-2f1f3c7a9e11",
  text: "Burst water main flooding Street 12 since fajr",
  location: "Gulshan-e-Iqbal Block 13-D",
  reporter_contact: null,
  category: "water",
  priority: "high",
  status: "open",
  ai_summary: "water: Burst water main flooding Street 12 since fajr",
  triaged_by: "rules:fallback",
  triage_confidence: 0.35,
  triage_latency_ms: 3,
  created_at: "2026-09-26T08:00:00Z",
  updated_at: "2026-09-26T08:00:00Z",
};

export const VALID_TEXT = "Burst water main flooding Street 12 since fajr";
export const VALID_LOCATION = "Gulshan-e-Iqbal Block 13-D";

/** A promise the test resolves or rejects by hand. */
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
