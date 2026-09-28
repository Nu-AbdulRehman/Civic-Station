// Display labels only (FR-FE-018 permits them): how a server value is shown, never which
// value applies. The keys are typed by the generated enum, so a new server value fails tsc.
import type { TriagedBy } from "./client";

export const PROVIDER_LABEL: Record<TriagedBy, string> = {
  "llm:groq": "Groq (hosted model)",
  "llm:ollama": "Ollama (local model)",
  rules: "keyword rules",
  "rules:fallback": "keyword rules (fallback)",
  simulated: "simulated classifier",
};

export function humanise(value: string): string {
  return value.replace(/_/g, " ");
}
